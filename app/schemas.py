from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class JobCreate(BaseModel):
    kind: Literal["convert", "cut", "merge", "extract"]
    payload: dict[str, Any]


class ContentSelection(BaseModel):
    audio: bool = True
    video: bool = True
    textgrid: bool = True

    @model_validator(mode="after")
    def at_least_one(self):
        if not (self.audio or self.video or self.textgrid):
            raise ValueError("音频、视频和 TextGrid 至少选择一项")
        return self


class BaseTask(BaseModel):
    input_root: str
    input_path: str = ""
    output_root: str
    output_path: str
    workers: int = Field(default=1, ge=1, le=4)
    overwrite: bool = False


class ConvertTask(BaseTask):
    mode: Literal["video_to_audio", "audio_to_audio", "video_to_video", "compress"]
    recursive: bool = True
    audio_codec: Literal["pcm_s16le", "libmp3lame", "aac", "flac", "libvorbis", "libopus"] = "pcm_s16le"
    audio_bitrate: str = "192k"
    sample_rate: int = Field(default=16000, ge=8000, le=192000)
    channels: int = Field(default=1, ge=1, le=8)
    video_codec: Literal["libx264", "libx265", "h264_qsv", "hevc_qsv", "libvpx-vp9", "mpeg4"] = "libx264"
    crf: int = Field(default=23, ge=0, le=51)
    resolution: str = ""
    preset: Literal["ultrafast", "fast", "medium", "slow", "veryslow"] = "medium"
    video_format: Literal[".mp4", ".mkv", ".webm"] = ".mp4"


class CutTask(BaseTask):
    content: ContentSelection = Field(default_factory=ContentSelection)
    segment_length: float = Field(default=300, ge=1, le=86400)
    use_sg_align: bool = True


class MergeTask(BaseTask):
    content: ContentSelection = Field(default_factory=ContentSelection)
    prefixes: list[str] = Field(default_factory=list)
    strict_triplets: bool = True


class RangeItem(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)

    @model_validator(mode="after")
    def valid_order(self):
        if self.end <= self.start:
            raise ValueError("区间结束时间必须大于开始时间")
        return self


class ExtractTask(BaseTask):
    content: ContentSelection = Field(default_factory=ContentSelection)
    base_name: str = Field(min_length=1, max_length=255)
    ranges: list[RangeItem] = Field(min_length=1, max_length=1000)


TASK_MODELS = {
    "convert": ConvertTask,
    "cut": CutTask,
    "merge": MergeTask,
    "extract": ExtractTask,
}


def validate_task(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    model = TASK_MODELS[kind].model_validate(payload)
    return model.model_dump(mode="json")
