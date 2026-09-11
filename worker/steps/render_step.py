"""Step 5: assemble scene assets into the final mp4.

Order of operations matters:
  1. every scene becomes a video-only segment;
  2. narration is concatenated separately — crossfading voice would clip words;
  3. segments are joined (hard cuts or crossfades);
  4. picture and voice are muxed;
  5. subtitles are burned in;
  6. music is mixed underneath.

Segments for crossfading are rendered `transition` seconds longer than their
narration, so the overlap eats exactly that tail and the finished video still
lasts as long as the voice track.
"""
from __future__ import annotations

import logging
from pathlib import Path

import media

log = logging.getLogger("worker.render")

# Последняя сцена рендерится чуть длиннее голоса: склейка через xfade теряет
# доли кадра на каждом переходе, и без запаса `-shortest` обрезал бы конец
# последней фразы. Лишний хвост потом отсекается по длине звука.
END_PAD_SEC = 0.5


def _scene_shots(scene: dict, measured_duration: float) -> list[dict]:
    """Кадры сцены, подогнанные под её настоящую озвучку.

    Планировщик считает длительности по значению из базы, а монтаж измеряет
    mp3 заново. Разница крошечная, но без подгонки она накапливается и уводит
    картинку от голоса — ровно тот дефект, что уже стоил проекту 0.217 с.
    """
    shots = scene.get("shots") or []
    if not shots:
        # Сцена без кадров ведёт себя как раньше: один кадр на всю длину.
        single = {"duration": measured_duration, "motion": media.DEFAULT_MOTION}
        if scene.get("clip_path"):
            single["clip_path"] = scene["clip_path"]
        else:
            single["image_path"] = scene["image_path"]
        return [single]

    planned = sum(float(s["duration"]) for s in shots)
    if planned <= 0:
        raise ValueError("сумма длительностей кадров сцены равна нулю")

    scale = measured_duration / planned
    fitted = [dict(s, duration=round(float(s["duration"]) * scale, 3)) for s in shots]
    # Остаток от округления отдаём последнему кадру, чтобы сумма совпала точно.
    drift = measured_duration - sum(s["duration"] for s in fitted)
    fitted[-1]["duration"] = round(fitted[-1]["duration"] + drift, 3)
    return fitted


def render_final(
    scenes: list[dict],
    work_dir: Path,
    music_file: str | None = None,
    aspect: str = media.DEFAULT_FORMAT,
    transition_sec: float = 0.0,
    subtitles: bool = True,
) -> Path:
    """Build the final video.

    Each scene dict must contain local paths and timing:
      audio_path (mp3), audio_duration (float), narration (str),
      and either clip_path (provider mp4) or image_path (still for Ken Burns).

    Сцена может содержать `shots` — список кадров камеры:
      {duration, motion, image_path | clip_path}.
    Тогда картинка сцены собирается из кадров встык, а плавный переход
    остаётся только на стыке сцен: внутри сцены склейка обязана читаться как
    склейка, иначе монтаж снова превращается в перелистывание.

    Без `shots` сцена ведёт себя как раньше — один кадр на всю длину.
    """
    size = media.frame_size(aspect)
    count = len(scenes)
    transition = transition_sec if count > 1 else 0.0
    # Таймлайн строится по фактической длине озвучки: голос — источник истины,
    # а оценка из заголовка mp3 накапливает расхождение с субтитрами.
    durations = [media.exact_duration_sec(Path(s["audio_path"])) for s in scenes]
    timed = [dict(s, audio_duration=d) for s, d in zip(scenes, durations)]

    log.info(
        "render: %d scenes, %s (%dx%d), transition %.2fs, subtitles %s",
        count, aspect, size[0], size[1], transition, subtitles,
    )

    # 1. картинка каждой сцены отдельно, без звука
    segments: list[Path] = []
    for i, scene in enumerate(scenes):
        tail = transition if i < count - 1 else END_PAD_SEC
        shots = _scene_shots(scene, durations[i])
        shot_segments: list[Path] = []
        for j, shot in enumerate(shots):
            # Запас под переход достаётся последнему кадру сцены: именно его
            # хвост съедает перекрёстное затухание со следующей сценой.
            extra = tail if j == len(shots) - 1 else 0.0
            seg = work_dir / f"segment_{i:02d}_{j:02d}.mp4"
            if shot.get("clip_path"):
                media.make_clip_segment(Path(shot["clip_path"]), seg, shot["duration"] + extra, size)
            else:
                media.make_motion_segment(
                    Path(shot["image_path"]), seg, shot["duration"] + extra, size,
                    shot.get("motion") or media.DEFAULT_MOTION,
                )
            shot_segments.append(seg)

        if len(shot_segments) == 1:
            segments.append(shot_segments[0])
        else:
            scene_seg = work_dir / f"segment_{i:02d}.mp4"
            media.concat_segments(shot_segments, scene_seg)
            segments.append(scene_seg)

    # 2. голос — встык, без перекрёстных затуханий
    voice = work_dir / "voice.m4a"
    media.concat_audio([Path(s["audio_path"]) for s in scenes], voice)

    # 3. склейка картинки
    picture = work_dir / "picture.mp4"
    if transition > 0:
        media.concat_with_transitions(segments, picture, durations, transition)
    else:
        media.concat_segments(segments, picture)

    # 4. картинка + голос; -shortest отсекает запасной хвост последней сцены,
    #    поэтому итоговая длина равна длине озвучки
    current = work_dir / "muxed.mp4"
    media.mux(picture, voice, current, duration=media.exact_duration_sec(voice))

    # 5. субтитры
    if subtitles:
        # .srt остаётся как отдельный артефакт для скачивания,
        # .ass используется для вшивания — у него точная привязка к кадру
        srt = work_dir / "subtitles.srt"
        srt.write_text(media.build_srt(timed), encoding="utf-8")
        _, family = media.resolve_font()
        ass = work_dir / "subtitles.ass"
        ass.write_text(media.build_ass(timed, size, family), encoding="utf-8")
        if srt.stat().st_size > 0:
            burned = work_dir / "subtitled.mp4"
            media.burn_subtitles(current, ass, burned)
            current = burned

    # 6. музыка
    if music_file:
        final = work_dir / "final.mp4"
        media.mix_music(current, Path(music_file), final)
        current = final

    return current
