__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2022 The OctoPrint Project - Released under terms of the AGPLv3 License"

from enum import Enum
from typing import Optional

from pydantic import BaseModel
from pydantic_settings import with_attrs_docs


class RatioEnum(str, Enum):
    sixteen_nine = "16:9"
    four_three = "4:3"


class TimelapseTypeEnum(str, Enum):
    off = "off"
    zchange = "zchange"
    timed = "timed"


@with_attrs_docs
class TimelapseOptions(BaseModel):
    interval: Optional[int] = None
    """`timed` timelapses only: The interval which to leave between images in seconds."""

    capturePostRoll: Optional[bool] = None
    """`timed` timelapses only: Whether to capture the snapshots for the post roll (true) or just copy the last captured snapshot from the print over and over again (false)."""

    retractionZHop: Optional[float] = None
    """`zchange` timelapses only: z-hop height during retractions to ignore for capturing snapshots."""


@with_attrs_docs
class TimelapseConfig(BaseModel):
    type: TimelapseTypeEnum = "off"
    """The timelapse type."""

    fps: int = 25
    """The framerate at which to render the movie."""

    postRoll: int = 0
    """The number of seconds in the rendered video to add after a finished print. The exact way how the additional images will be recorded depends on timelapse type. `zchange` timelapses will take one final picture and add it `fps * postRoll` times. `timed` timelapses continue to record just like at the beginning, so the recording will continue another `fps * postRoll * interval` seconds. This behaviour can be overridden by setting the `capturePostRoll` option to `false`, in which case the post roll will be created identically to `zchange` mode."""

    options: TimelapseOptions = TimelapseOptions()
    """Additional options depending on the timelapse type."""


@with_attrs_docs
class WebcamConfig(BaseModel):
    webcamEnabled: bool = True
    """Use this option to enable display of a webcam stream in the UI, e.g. via MJPG-Streamer. Webcam support will be disabled if not set."""

    timelapseEnabled: bool = True
    """Use this option to enable timelapse support via snapshot, e.g. via MJPG-Streamer. Timelapse support will be disabled if not set."""

    ffmpeg: Optional[str] = None
    """Path to ffmpeg binary to use for creating timelapse recordings. Timelapse support will be disabled if not set."""

    ffmpegThreads: int = 1
    """Number of how many threads to instruct ffmpeg to use for encoding."""

    ffmpegVideoCodec: str = "libx264"
    """Videocodec to be used for encoding."""

    bitrate: str = "10000k"
    """The bitrate to use for rendering the timelapse video. This gets directly passed to ffmpeg."""

    watermark: bool = True
    """Whether to include a "created with OctoPrint" watermark in the generated timelapse recordings."""

    ffmpegCommandline: str = '{ffmpeg} -framerate {fps} -i "{input}" -vcodec {videocodec} -threads {threads} -b:v {bitrate} -f {containerformat} -y {filters} "{output}"'

    ffmpegThumbnailCommandline: str = (
        '{ffmpeg} -sseof -1 -i "{input}" -update 1 -q:v 0.7 "{output}"'
    )

    timelapse: TimelapseConfig = TimelapseConfig()
    """The default timelapse settings."""

    cleanTmpAfterDays: int = 7
    """After how many days unrendered timelapses will be deleted."""

    defaultWebcam: str = "classic"
    """The name of the default webcam"""


@with_attrs_docs
class WebcamCompatibility(BaseModel):

    streamTimeout: int = 5
    """The timeout of the stream in seconds"""

    streamRatio: RatioEnum = RatioEnum.sixteen_nine
    """The stream's native aspect ratio"""

    streamWebrtcIceServers: str = "stun:stun.l.google.com:19302"
    """The WebRTC STUN and TURN servers, comma separated"""

    cacheBuster: bool = False
    """Whether the the URL should be randomized to bust caches"""

    stream: str
    """The URL to get an MJPEG stream from"""

    snapshot: str = None
    """The URL to get the snapshot from"""

    snapshotTimeout: int = 5
    """The timeout when retrieving snapshots"""

    snapshotSslValidation: bool = True
    """Whether to validate SSL certificates when retrieving a snapshot"""


@with_attrs_docs
class Webcam(BaseModel):

    name: str
    """Identifier of this webcam"""

    displayName: str
    """Displayable name for this webcam"""

    canSnapshot: bool = False
    """Whether this webcam can take a snapshot."""

    snapshotDisplay: str = None
    """Human readable information about how a snapshot is captured or a HTTP URL from which the snapshot is loaded (optional, only for user reference)"""

    flipH: bool = False
    """Whether to flip the webcam horizontally."""

    flipV: bool = False
    """Whether to flip the webcam vertically."""

    rotate90: bool = False
    """Whether to rotate the webcam 90° counter clockwise."""

    extras: dict = None
    """Unstructured data describing this webcam"""

    compat: WebcamCompatibility = None
    """A compatibility configuration to allow older clients to make use of this webcam"""
