__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2020 The OctoPrint Project - Released under terms of the AGPLv3 License"

from flask_babel import gettext

import octoprint.plugin
from octoprint.webcams import LegacyWebcamConfiguration, WebcamConfiguration


class MjpegWebcamPlugin(
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.WebcamPlugin,
):
    def get_assets(self):
        return {
            "js": ["js/classicwebcam.js", "js/classicwebcam_settings.js"],
            "less": ["less/classicwebcam.less"],
            "css": ["css/classicwebcam.css"],
        }

    def get_template_configs(self):
        return [
            {
                "type": "settings",
                "template": "classicwebcam_settings.jinja2",
                "custom_bindings": True,
            },
            {
                "type": "webcam",
                "name": "Classic Webcam",
                "template": "classicwebcam_webcam.jinja2",
                "custom_bindings": True,
                "suffix": "_real",
            },
            {
                "type": "webcam",
                "name": "Dummy Webcam",
                "template": "classicwebcam_webcam_2.jinja2",
                "custom_bindings": False,
                "suffix": "_dummy",
            },
        ]

    def get_webcam_configurations(self):
        return [
            WebcamConfiguration(
                name="classic",
                display_name="Classic Webcam",
                snapshot=self._settings.get(["snapshot"]),
                flip_h=self._settings.get(["flipH"]),
                flip_v=self._settings.get(["flipV"]),
                rotate_90=self._settings.get(["rotate90"]),
                legacy=LegacyWebcamConfiguration(
                    snapshot=self._settings.get(["snapshot"]),
                    flip_h=self._settings.get(["flipH"]),
                    flip_v=self._settings.get(["flipV"]),
                    rotate_90=self._settings.get(["rotate90"]),
                    stream=self._settings.get(["stream"]),
                    stream_timeout=self._settings.get(["streamTimeout"]),
                    stream_ratio=self._settings.get(["streamRatio"]),
                    stream_webrtc_ice_servers=self._settings.get(
                        ["streamWebrtcIceServers"]
                    ),
                    cache_buster=self._settings.get(["cacheBuster"]),
                ),
                attachments=dict(
                    stream=self._settings.get(["stream"]),
                    streamTimeout=self._settings.get(["streamTimeout"]),
                    streamRatio=self._settings.get(["streamRatio"]),
                    streamWebrtcIceServers=self._settings.get(["streamWebrtcIceServers"]),
                    cacheBuster=self._settings.get(["cacheBuster"]),
                ),
            )
        ]

    def get_settings_defaults(self):
        return dict(
            flipH=False,
            flipV=False,
            rotate90=False,
            stream="",
            streamTimeout=5,
            streamRatio="4:3",
            streamWebrtcIceServers="stun:stun.l.google.com:19302",
            snapshot="",
            cacheBuster=False,
        )

    def get_settings_version(self):
        return 1

    def on_settings_migrate(self, target, current):
        if current is None:
            config = self._settings.global_get(["webcam"])
            if config:
                self._logger.info(
                    "Migrating settings from webcam to plugins.classicwebcam..."
                )

                self._settings.set_boolean(
                    ["flipH"], config.get("flipH", False), force=True
                )
                self._settings.global_remove(["webcam", "flipH"])

                self._settings.set_boolean(
                    ["flipV"], config.get("flipV", False), force=True
                )
                self._settings.global_remove(["webcam", "flipV"])

                self._settings.set_boolean(
                    ["rotate90"], config.get("rotate90", False), force=True
                )
                self._settings.global_remove(["webcam", "rotate90"])

                self._settings.set(["stream"], config.get("stream", ""), force=True)
                self._settings.global_remove(["webcam", "stream"])

                self._settings.set_int(
                    ["streamTimeout"], config.get("streamTimeout", ""), force=True
                )
                self._settings.global_remove(["webcam", "streamTimeout"])

                self._settings.set(
                    ["streamRatio"], config.get("streamRatio", ""), force=True
                )
                self._settings.global_remove(["webcam", "streamRatio"])

                self._settings.set(
                    ["streamWebrtcIceServers"],
                    ",".join(
                        config.get(
                            "streamWebrtcIceServers", ["stun:stun.l.google.com:19302"]
                        )
                    ),
                    force=True,
                )
                self._settings.global_remove(["webcam", "streamWebrtcIceServers"])

                self._settings.set(["snapshot"], config.get("snapshot", ""), force=True)
                self._settings.global_remove(["webcam", "snapshot"])

                self._settings.set_boolean(
                    ["cacheBuster"], config.get("cacheBuster", ""), force=True
                )
                self._settings.global_remove(["webcam", "cacheBuster"])


__plugin_name__ = gettext("Classic Webcam")
__plugin_author__ = "Christian Würthner"
__plugin_description__ = "Provides a simple webcam viewer in OctoPrint's UI, images provided by an MJPEG webcam."
__plugin_disabling_discouraged__ = gettext(
    "Without this plugin the basic Webcam in the control tab"
    " will no longer be available."
)
__plugin_license__ = "AGPLv3"
__plugin_pythoncompat__ = ">=3.7,<4"
__plugin_implementation__ = MjpegWebcamPlugin()
