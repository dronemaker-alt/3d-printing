# coding=utf-8
from __future__ import absolute_import, division, print_function

__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"


def commands(cli_group, pass_octoprint_ctx, *args, **kwargs):
	import click
	click.disable_unicode_literals_warning = True
	import sys
	import requests.exceptions
	import octoprint_client as client

	@click.command("check")
	@click.option("--force", is_flag=True, help="Ignore the cache for the update check")
	@click.argument("targets", nargs=-1)
	def check_command(force, targets):
		"""Check for updates."""
		params = dict(force=force)
		if targets:
			params["check"] = ",".join(targets)

		client.init_client(cli_group.settings)
		r = client.get("plugin/softwareupdate/check", params=params)
		try:
			r.raise_for_status()
		except requests.exceptions.HTTPError as e:
			click.echo("Could not get update information from server, got {}".format(e))
			sys.exit(1)

		data = r.json()
		status = data["status"]
		information = data["information"]

		lines = []
		octoprint_line = None
		for key, info in information.items():
			status_text = "Up to date"
			if info["updateAvailable"]:
				if info["updatePossible"]:
					status_text = "Update available"
				else:
					status_text = "Update available (manual)"
			line = "{}\n\tInstalled: {}\n\tAvailable: {}\n\t=> {}".format(info["displayName"],
			                                                              info["information"]["local"]["name"],
			                                                              info["information"]["remote"]["name"],
			                                                              status_text)
			if key == "octoprint":
				octoprint_line = line
			else:
				lines.append(line)

		lines.sort()
		if octoprint_line:
			lines = [octoprint_line] + lines

		for line in lines:
			click.echo(line)

		click.echo()
		if status == "current":
			click.echo("Everything is up to date")
		else:
			click.echo("There are updates available!")


	@click.command("update")
	@click.option("--force", is_flag=True, help="Update even if already up to date")
	@click.argument("targets", nargs=-1)
	def update_command(force, targets):
		"""Apply updates."""

		data = dict(force=force)
		if targets:
			data["check"] = targets

		client.init_client(cli_group.settings)

		flags = dict(
			waiting_for_restart=False,
			seen_close=False
		)

		def on_message(ws, msg_type, msg):
			if msg_type != "plugin" or msg["plugin"] != "softwareupdate":
				return

			plugin_message = msg["data"]
			if not "type" in plugin_message:
				return

			plugin_message_type = plugin_message["type"]
			plugin_message_data = plugin_message["data"]

			if plugin_message_type == "updating":
				click.echo("Updating {} to {}...".format(plugin_message_data["name"], plugin_message_data["target"]))

			elif plugin_message_type == "update_failed":
				click.echo("\t... failed :(")

			elif plugin_message_type == "loglines" and "loglines" in plugin_message_data:
				for entry in plugin_message_data["loglines"]:
					prefix = ">>> " if entry["stream"] == "call" else ""
					error = entry["stream"] == "stderr"
					click.echo("\t{}{}".format(prefix, entry["line"].replace("\n", "\n\t")), err=error)

			elif plugin_message_type == "success" or plugin_message_type == "restart_manually":
				results = plugin_message_data["results"] if "results" in plugin_message_data else dict()
				if results:
					click.echo("The update finished successfully.")
					if plugin_message_type == "restart_manually":
						click.echo("Please restart the OctoPrint server.")
				else:
					click.echo("No update necessary")
				ws.close()

			elif plugin_message_type == "restarting":
				flags["waiting_for_restart"] = True
				click.echo("Restarting to apply changes...")

			elif plugin_message_type == "failure":
				click.echo("Error")
				ws.close()

		def on_open(ws):
			if flags["waiting_for_restart"] and flags["seen_close"]:
				click.echo(" Reconnected!")
			else:
				click.echo("Connected to server...")

		def on_close(ws):
			if flags["waiting_for_restart"] and flags["seen_close"]:
				click.echo(".", nl=False)
			else:
				flags["seen_close"] = True
				click.echo("Disconnected from server...")

		socket = client.connect_socket(on_message=on_message,
		                               on_open=on_open,
		                               on_close=on_close)

		r = client.post_json("plugin/softwareupdate/update", data=data)
		try:
			r.raise_for_status()
		except requests.exceptions.HTTPError as e:
			click.echo("Could not get update information from server, got {}".format(e))
			sys.exit(1)

		data = r.json()
		to_be_updated = data["order"]
		checks = data["checks"]
		click.echo("Update in progress, updating:")
		for name in to_be_updated:
			click.echo("\t{}".format(name if not name in checks else checks[name]))

		socket.wait()

		if flags["waiting_for_restart"]:
			if socket.reconnect(timeout=60):
				click.echo("The update finished successfully.")
			else:
				click.echo("The update finished successfully but the server apparently didn't restart as expected.")
				click.echo("Please restart the OctoPrint server.")

	return [check_command, update_command]


