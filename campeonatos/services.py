"""
Servicios de dominio para la gestión de Campeonatos:
- Generación de usuarios efímeros para jueces de Tatami.
- Motor de competición por Puntuación (corte Top N, detección de empates y creación
  automática de nuevas rondas de desempate).
- Motor de competición por Banderas / Kumite (eliminatoria directa Aka vs Ao).
- Consolidación de actas en ResultadoHistorico inmutable.
"""
import secrets
import string
from collections import Counter

from django.contrib.auth.models import Group
from django.db import transaction
from django.utils.text import slugify

from usuarios.models import Usuario
from administracion.permissions import JUEZ_TATAMI_GROUP_NAME
from campeonatos.models import (
    ActuacionPuntuacion,
    EnfrentamientoBanderas,
    ResultadoHistorico,
    RondaCategoria,
)


def crear_credenciales_juez_tatami(tatami, password_plano=None):
    """
    Crea o actualiza el usuario efímero asignado a un Tatami dentro del grupo JuezTatami.
    Devuelve (usuario, email, password_plano).
    """
    grupo_juez, _ = Group.objects.get_or_create(name=JUEZ_TATAMI_GROUP_NAME)
    torneo_slug = slugify(tatami.campeonato.nombre)[:25] or f"torneo{tatami.campeonato_id}"
    email_juez = f"tatami{tatami.numero}_{torneo_slug}@tatami.ogkke.es"

    if not password_plano:
        alfabeto = string.ascii_letters + string.digits
        password_plano = "Tatami" + "".join(secrets.choice(alfabeto) for _ in range(6)) + "!"

    usuario, creado = Usuario.objects.get_or_create(
        email=email_juez,
        defaults={
            'username': email_juez,
            'first_name': f"Mesa Tatami {tatami.numero}",
            'last_name': tatami.campeonato.nombre[:80],
            'is_active': True,
            'is_staff': False,
            'externo': True,
        }
    )
    usuario.set_password(password_plano)
    usuario.is_active = True
    usuario.save()
    usuario.groups.add(grupo_juez)

    tatami.juez_operador = usuario
    tatami.save(update_fields=['juez_operador'])
    return usuario, email_juez, password_plano


@transaction.atomic
def iniciar_competicion_categoria(categoria):
    """
    Inicia la primera ronda de una categoría según su sistema (PUNTOS o BANDERAS/KUMITE).
    """
    inscripciones = list(
        categoria.inscripciones.filter(descalificado=False).order_by('orden_salida_inicial', 'id')
    )
    if not inscripciones:
        raise ValueError("No hay competidores inscritos activos en esta categoría.")

    # Si ya existen rondas, devolvemos la última activa
    ronda_existente = categoria.rondas.order_by('-numero').first()
    if ronda_existente:
        return ronda_existente

    categoria.estado = 'EN_CURSO'
    categoria.save(update_fields=['estado'])

    if categoria.campeonato.estado in ('BORRADOR', 'INSCRIPCION'):
        categoria.campeonato.estado = 'EN_CURSO'
        categoria.campeonato.save(update_fields=['estado'])

    if categoria.sistema == 'PUNTOS':
        es_final_directa = len(inscripciones) <= categoria.clasificados_siguiente_ronda
        ronda = RondaCategoria.objects.create(
            categoria=categoria,
            numero=1,
            nombre="Ronda Final Directa" if es_final_directa else "Ronda Clasificatoria",
            es_final=es_final_directa,
            es_desempate=False,
        )
        for idx, insc in enumerate(inscripciones, start=1):
            ActuacionPuntuacion.objects.create(
                ronda=ronda,
                inscripcion=insc,
                orden_salida=idx,
            )
        return ronda

    # Sistema BANDERAS (Kata por banderas o Kumite)
    es_final_directa = len(inscripciones) <= 2
    ronda = RondaCategoria.objects.create(
        categoria=categoria,
        numero=1,
        nombre="Final Directa" if es_final_directa else "Ronda Eliminatoria 1",
        es_final=es_final_directa,
        es_desempate=False,
    )
    _generar_enfrentamientos_ronda(ronda, inscripciones)
    return ronda


def _generar_enfrentamientos_ronda(ronda, lista_inscripciones):
    """Empareja la lista de inscripciones 1 contra 1 (Aka vs Ao). Si es impar, el último pasa por Bye."""
    orden = 1
    idx = 0
    total = len(lista_inscripciones)
    while idx < total:
        aka = lista_inscripciones[idx]
        ao = lista_inscripciones[idx + 1] if (idx + 1) < total else None
        es_bye = ao is None
        EnfrentamientoBanderas.objects.create(
            ronda=ronda,
            orden_combate=orden,
            aka_inscripcion=aka,
            ao_inscripcion=ao,
            ganador=aka if es_bye else None,
            finalizado=es_bye,
        )
        orden += 1
        idx += 2


@transaction.atomic
def cerrar_y_avanzar_ronda_puntuacion(ronda):
    """
    Cierra una ronda de puntuación:
    - En rondas clasificatorias: selecciona los Top N mejores. Si hay empate en la línea
      de corte N, crea automáticamente una nueva Ronda de Desempate solo con los empatados.
    - En ronda final: verifica los 3 primeros puestos de podio. Si hay empate en medallas,
      crea una nueva Ronda de Desempate de Podio. Cuando queda resuelto, consolida el
      ResultadoHistorico inmutable.
    """
    categoria = ronda.categoria
    actuaciones = list(
        ronda.actuaciones.select_related('inscripcion').order_by('-nota_total', '-nota_media', 'orden_salida')
    )
    if not actuaciones or any(not a.evaluado for a in actuaciones):
        raise ValueError("Todos los competidores de la ronda deben estar puntuados antes de cerrar la ronda.")

    top_n = categoria.clasificados_siguiente_ronda

    # CASO 1: Ronda clasificatoria o desempate de corte (aún no es la final)
    if not ronda.es_final:
        # Recuperar quienes ya estaban clasificados directamente en rondas previas no finales
        clasificados_previos_ids = list(
            ActuacionPuntuacion.objects.filter(
                ronda__categoria=categoria,
                ronda__es_final=False,
                ronda__numero__lt=ronda.numero,
                clasificado=True,
            ).values_list('inscripcion_id', flat=True).distinct()
        )
        plazas_restantes = max(0, top_n - len(clasificados_previos_ids))

        if len(actuaciones) <= plazas_restantes:
            for act in actuaciones:
                act.clasificado = True
                act.save(update_fields=['clasificado'])
            ronda.cerrada = True
            ronda.save(update_fields=['cerrada'])
            return _crear_ronda_final_puntuacion(categoria, ronda.numero + 1)

        nota_corte = actuaciones[plazas_restantes - 1].nota_total
        superiores = [a for a in actuaciones if a.nota_total > nota_corte]
        empatados_corte = [a for a in actuaciones if a.nota_total == nota_corte]

        # Si los que superan la nota de corte + los empatados en la nota de corte exceden las plazas
        if len(superiores) + len(empatados_corte) > plazas_restantes:
            for act in superiores:
                act.clasificado = True
                act.save(update_fields=['clasificado'])
            ronda.cerrada = True
            ronda.save(update_fields=['cerrada'])

            plazas_en_juego = plazas_restantes - len(superiores)
            ronda_desempate = RondaCategoria.objects.create(
                categoria=categoria,
                numero=ronda.numero + 1,
                nombre=f"Desempate de Clasificación ({plazas_en_juego} plaza/s)",
                es_final=False,
                es_desempate=True,
            )
            for idx, act_emp in enumerate(empatados_corte, start=1):
                ActuacionPuntuacion.objects.create(
                    ronda=ronda_desempate,
                    inscripcion=act_emp.inscripcion,
                    orden_salida=idx,
                )
            return {
                'estado': 'DESEMPATE_CORTE',
                'ronda_creada': ronda_desempate,
                'mensaje': (
                    f"Empate detectado en el corte ({nota_corte} pts) entre {len(empatados_corte)} competidores "
                    f"para {plazas_en_juego} plaza(s). Se ha creado una nueva ronda de desempate."
                ),
            }

        # Sin empate en el corte: clasifican los primeros `plazas_restantes`
        for act in actuaciones[:plazas_restantes]:
            act.clasificado = True
            act.save(update_fields=['clasificado'])
        ronda.cerrada = True
        ronda.save(update_fields=['cerrada'])
        return _crear_ronda_final_puntuacion(categoria, ronda.numero + 1)

    # CASO 2: Ronda Final o Desempate de Podio (`ronda.es_final == True`)
    # Construimos la clasificación combinada de la Final + posibles desempates de podio posteriores
    ronda_final_base = (
        categoria.rondas.filter(es_final=True, es_desempate=False).order_by('numero').first()
        or ronda
    )
    actuaciones_base = list(
        ronda_final_base.actuaciones.select_related('inscripcion').order_by('-nota_total', 'orden_salida')
    )
    # Mapa de notas de desempate de podio posteriores por inscripcion_id
    desempates_podio = (
        ActuacionPuntuacion.objects.filter(
            ronda__categoria=categoria,
            ronda__es_final=True,
            ronda__es_desempate=True,
            evaluado=True,
        )
        .order_by('ronda__numero')
    )
    bonus_desempate = {}
    for dp in desempates_podio:
        bonus_desempate.setdefault(dp.inscripcion_id, []).append(dp.nota_total)

    def clave_ordenacion_final(act):
        desempates = tuple(bonus_desempate.get(act.inscripcion_id, []))
        return (act.nota_total, desempates)

    ordenadas = sorted(actuaciones_base, key=clave_ordenacion_final, reverse=True)
    # Comprobar si entre los 3 primeros puestos (medallas) persiste algún empate exacto
    top_medallas = ordenadas[:4]
    conteo_claves = Counter(clave_ordenacion_final(a) for a in top_medallas)
    claves_empatadas_en_podio = {
        clave for idx, (clave, _) in enumerate(
            [(clave_ordenacion_final(a), a) for a in ordenadas[:3]]
        )
        if conteo_claves[clave] > 1
    }

    if claves_empatadas_en_podio:
        empatados_podio = [a for a in ordenadas if clave_ordenacion_final(a) in claves_empatadas_en_podio]
        ronda.cerrada = True
        ronda.save(update_fields=['cerrada'])

        ronda_desempate_podio = RondaCategoria.objects.create(
            categoria=categoria,
            numero=ronda.numero + 1,
            nombre="Ronda de Desempate de Podio",
            es_final=True,
            es_desempate=True,
        )
        for idx, act_emp in enumerate(empatados_podio, start=1):
            ActuacionPuntuacion.objects.create(
                ronda=ronda_desempate_podio,
                inscripcion=act_emp.inscripcion,
                orden_salida=idx,
            )
        return {
            'estado': 'DESEMPATE_PODIO',
            'ronda_creada': ronda_desempate_podio,
            'mensaje': (
                f"Empate detectado en puestos de podio entre {len(empatados_podio)} competidores. "
                "Se ha generado una nueva Ronda de Desempate de Podio."
            ),
        }

    # Sin empates en el podio -> cerrar ronda, consolidar histórico y finalizar categoría
    ronda.cerrada = True
    ronda.save(update_fields=['cerrada'])

    ResultadoHistorico.objects.filter(categoria=categoria).delete()
    for puesto_idx, act in enumerate(ordenadas[:4], start=1):
        act.clasificado = puesto_idx <= 3
        act.save(update_fields=['clasificado'])
        insc = act.inscripcion
        notas_extra = bonus_desempate.get(insc.id)
        marca_str = f"{act.nota_total} pts"
        if notas_extra:
            marca_str += f" (Desempate: {notas_extra[-1]} pts)"
        ResultadoHistorico.objects.create(
            campeonato=categoria.campeonato,
            categoria=categoria,
            puesto=puesto_idx,
            inscripcion=insc,
            nombre_competidor_snapshot=insc.nombre_competidor,
            dojo_nombre_snapshot=insc.dojo_nombre,
            grado_snapshot=insc.grado_mostrable,
            modalidad_snapshot=categoria.modalidad,
            puntuacion_final_snapshot=marca_str,
        )

    categoria.estado = 'FINALIZADA'
    categoria.save(update_fields=['estado'])
    return {
        'estado': 'FINALIZADA',
        'ronda_creada': None,
        'mensaje': f"Categoría '{categoria.nombre}' finalizada y acta histórica consolidada.",
    }


def _crear_ronda_final_puntuacion(categoria, siguiente_numero):
    """Crea la Ronda Final con todos los competidores marcados como clasificado=True."""
    actuaciones_clasificadas = (
        ActuacionPuntuacion.objects.filter(
            ronda__categoria=categoria,
            ronda__es_final=False,
            clasificado=True,
        )
        .select_related('inscripcion')
        .order_by('ronda__numero', '-nota_total', 'orden_salida')
    )
    inscripciones_final = []
    vistos = set()
    for act in actuaciones_clasificadas:
        if act.inscripcion_id not in vistos:
            vistos.add(act.inscripcion_id)
            inscripciones_final.append(act.inscripcion)

    ronda_final = RondaCategoria.objects.create(
        categoria=categoria,
        numero=siguiente_numero,
        nombre="Ronda Final",
        es_final=True,
        es_desempate=False,
    )
    for idx, insc in enumerate(inscripciones_final, start=1):
        ActuacionPuntuacion.objects.create(
            ronda=ronda_final,
            inscripcion=insc,
            orden_salida=idx,
        )
    return {
        'estado': 'RONDA_FINAL_CREADA',
        'ronda_creada': ronda_final,
        'mensaje': f"Clasificados los {len(inscripciones_final)} mejores competidores a la Ronda Final.",
    }


@transaction.atomic
def cerrar_y_avanzar_ronda_banderas(ronda):
    """
    Cierra una ronda de eliminatorias (Banderas Aka/Ao o Kumite) y genera la siguiente
    ronda del cuadro o consolida el podio final en ResultadoHistorico.
    """
    categoria = ronda.categoria
    combates = list(
        ronda.enfrentamientos.select_related('aka_inscripcion', 'ao_inscripcion', 'ganador').order_by('orden_combate')
    )
    if not combates or any(not c.finalizado or not c.ganador_id for c in combates):
        raise ValueError("Todos los enfrentamientos de la ronda deben tener un ganador antes de avanzar.")

    ronda.cerrada = True
    ronda.save(update_fields=['cerrada'])

    if ronda.es_final:
        combate_final = next((c for c in combates if not c.es_tercer_puesto), combates[0])
        combate_bronce = next((c for c in combates if c.es_tercer_puesto), None)

        oro = combate_final.ganador
        plata = (
            combate_final.ao_inscripcion
            if combate_final.ganador_id == combate_final.aka_inscripcion_id
            else combate_final.aka_inscripcion
        )

        ResultadoHistorico.objects.filter(categoria=categoria).delete()
        podio = [(1, oro, combate_final.marcador_resumen)]
        if plata:
            podio.append((2, plata, "Subcampeón"))

        if combate_bronce and combate_bronce.ganador:
            bronce = combate_bronce.ganador
            cuarto = (
                combate_bronce.ao_inscripcion
                if combate_bronce.ganador_id == combate_bronce.aka_inscripcion_id
                else combate_bronce.aka_inscripcion
            )
            podio.append((3, bronce, combate_bronce.marcador_resumen))
            if cuarto:
                podio.append((4, cuarto, "Finalista"))

        for puesto, insc, resumen in podio:
            ResultadoHistorico.objects.create(
                campeonato=categoria.campeonato,
                categoria=categoria,
                puesto=puesto,
                inscripcion=insc,
                nombre_competidor_snapshot=insc.nombre_competidor,
                dojo_nombre_snapshot=insc.dojo_nombre,
                grado_snapshot=insc.grado_mostrable,
                modalidad_snapshot=categoria.modalidad,
                puntuacion_final_snapshot=resumen,
            )

        categoria.estado = 'FINALIZADA'
        categoria.save(update_fields=['estado'])
        return {
            'estado': 'FINALIZADA',
            'ronda_creada': None,
            'mensaje': f"Categoría '{categoria.nombre}' finalizada y podio registrado en el histórico.",
        }

    ganadores = [c.ganador for c in combates if not c.es_tercer_puesto and c.ganador]
    perdedores = []
    for c in combates:
        if not c.es_tercer_puesto and c.ao_inscripcion is not None:
            perdedor = c.ao_inscripcion if c.ganador_id == c.aka_inscripcion_id else c.aka_inscripcion
            if perdedor:
                perdedores.append(perdedor)

    es_siguiente_final = len(ganadores) <= 2
    nueva_ronda = RondaCategoria.objects.create(
        categoria=categoria,
        numero=ronda.numero + 1,
        nombre="Ronda Final" if es_siguiente_final else f"Ronda Eliminatoria {ronda.numero + 1}",
        es_final=es_siguiente_final,
        es_desempate=False,
    )
    _generar_enfrentamientos_ronda(nueva_ronda, ganadores)

    # Si es la ronda final y hubo 2 perdedores en semifinales, crear cruce por el 3º puesto (Bronce)
    if es_siguiente_final and len(perdedores) >= 2:
        EnfrentamientoBanderas.objects.create(
            ronda=nueva_ronda,
            orden_combate=2,
            aka_inscripcion=perdedores[0],
            ao_inscripcion=perdedores[1],
            es_tercer_puesto=True,
            finalizado=False,
        )

    return {
        'estado': 'SIGUIENTE_RONDA_CREADA',
        'ronda_creada': nueva_ronda,
        'mensaje': f"Avance completado: creada {nueva_ronda.nombre}.",
    }
