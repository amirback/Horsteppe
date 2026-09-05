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
        seg_duration = durations[i] + tail
        seg = work_dir / f"segment_{i:02d}.mp4"
        if scene.get("clip_path"):
            media.make_clip_segment(Path(scene["clip_path"]), seg, seg_duration, size)
        else:
            media.make_kenburns_segment(Path(scene["image_path"]), seg, seg_duration, size)
        segments.append(seg)

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
