# coding=utf-8
from __future__ import absolute_import, division, print_function

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import requests
import logging

from ..exceptions import ConfigurationInvalid

RELEASE_URL = "https://api.github.com/repos/{user}/{repo}/releases"

logger = logging.getLogger("octoprint.plugins.softwareupdate.version_checks.github_release")

def _filter_out_latest(releases,
                       sort_key=None,
                       include_prerelease=False,
                       prerelease_channel=None):
	"""
	Filters out the newest of all matching releases.

	Tests:

	    >>> release_1_2_15 = dict(name="1.2.15", tag_name="1.2.15", html_url="some_url", published_at="2016-07-29T19:53:29Z", prerelease=False, draft=False, target_commitish="prerelease")
	    >>> release_1_2_16rc1 = dict(name="1.2.16rc1", tag_name="1.2.16rc1", html_url="some_url", published_at="2016-08-29T12:00:00Z", prerelease=True, draft=False, target_commitish="rc/maintenance")
	    >>> release_1_2_16rc2 = dict(name="1.2.16rc2", tag_name="1.2.16rc2", html_url="some_url", published_at="2016-08-30T12:00:00Z", prerelease=True, draft=False, target_commitish="rc/maintenance")
	    >>> release_1_2_17rc1 = dict(name="1.2.17rc1", tag_name="1.2.17rc1", html_url="some_url", published_at="2016-08-31T12:00:00Z", prerelease=True, draft=True, target_commitish="rc/maintenance")
	    >>> release_1_3_0rc1 = dict(name="1.3.0rc1", tag_name="1.3.0rc1", html_url="some_url", published_at="2016-12-12T12:00:00Z", prerelease=True, draft=False, target_commitish="rc/devel")
	    >>> release_1_2_18 = dict(name="1.2.18", tag_name="1.2.18", html_url="some_url", published_at="2016-12-13T12:00:00Z", prerelease=False, draft=False, target_commitish="master")
	    >>> release_1_4_0rc1 = dict(name="1.4.0rc1", tag_name="1.4.0rc1", html_url="some_url", published_at="2017-12-12T12:00:00Z", prerelease=True, draft=False, target_commitish="rc/future")
	    >>> releases = [release_1_2_15, release_1_2_16rc1, release_1_2_16rc2, release_1_2_17rc1, release_1_3_0rc1, release_1_4_0rc1]
	    >>> _filter_out_latest(releases, include_prerelease=False, prerelease_channel=None)
	    ('1.2.15', '1.2.15', 'some_url')
	    >>> _filter_out_latest(releases, include_prerelease=True, prerelease_channel="rc/maintenance")
	    ('1.2.16rc2', '1.2.16rc2', 'some_url')
	    >>> _filter_out_latest(releases, include_prerelease=True, prerelease_channel="rc/devel")
	    ('1.3.0rc1', '1.3.0rc1', 'some_url')
	    >>> _filter_out_latest(releases, include_prerelease=True, prerelease_channel=None)
	    ('1.4.0rc1', '1.4.0rc1', 'some_url')
	    >>> _filter_out_latest(releases, include_prerelease=True, prerelease_channel="rc/doesntexist")
	    ('1.2.15', '1.2.15', 'some_url')
	    >>> _filter_out_latest([release_1_2_17rc1])
	    (None, None, None)
	    >>> _filter_out_latest([release_1_2_16rc1, release_1_2_16rc2])
	    (None, None, None)
	    >>> comparable_factory = _get_comparable_factory("python", force_base=True)
	    >>> sort_key = lambda release: comparable_factory(_get_sanitized_version(release["tag_name"]))
	    >>> _filter_out_latest(releases + [release_1_2_18], include_prerelease=False, prerelease_channel=None, sort_key=sort_key)
	    ('1.2.18', '1.2.18', 'some_url')
	    >>> _filter_out_latest(releases + [release_1_2_18], include_prerelease=True, prerelease_channel="rc/maintenance", sort_key=sort_key)
	    ('1.2.18', '1.2.18', 'some_url')
	    >>> _filter_out_latest(releases + [release_1_2_18], include_prerelease=True, prerelease_channel="rc/devel", sort_key=sort_key)
	    ('1.3.0rc1', '1.3.0rc1', 'some_url')
	"""

	nothing = None, None, None

	if sort_key is None:
		sort_key = lambda release: release.get("published_at", None)

	# filter out prereleases and drafts
	filter_function = lambda rel: not rel["prerelease"] and not rel["draft"]
	if include_prerelease:
		if prerelease_channel:
			filter_function = lambda rel: not rel["draft"] and (
			not rel["prerelease"] or rel["target_commitish"] == prerelease_channel)
		else:
			filter_function = lambda rel: not rel["draft"]

	releases = filter(filter_function, releases)
	if not releases:
		return nothing

	# sort by sort_key
	releases = sorted(releases, key=sort_key)

	# latest release = last in list
	latest = releases[-1]

	return latest["name"], latest["tag_name"], latest.get("html_url", None)


def _get_latest_release(user, repo, compare_type,
                        include_prerelease=False,
                        prerelease_channel=None,
                        force_base=True):
	nothing = None, None, None
	r = requests.get(RELEASE_URL.format(user=user, repo=repo))

	from . import log_github_ratelimit
	log_github_ratelimit(logger, r)

	if not r.status_code == requests.codes.ok:
		return nothing

	releases = r.json()

	# sanitize
	required_fields = {"name", "tag_name", "html_url", "draft", "prerelease", "published_at", "target_commitish"}
	releases = filter(lambda rel: set(rel.keys()) & required_fields == required_fields,
	                  releases)

	comparable_factory = _get_comparable_factory(compare_type,
	                                             force_base=force_base)
	sort_key = lambda release: comparable_factory(_get_sanitized_version(release["tag_name"]))

	return _filter_out_latest(releases,
	                          sort_key=sort_key,
	                          include_prerelease=include_prerelease,
	                          prerelease_channel=prerelease_channel)


def _get_sanitized_version(version_string):
	"""
	Removes "-..." prefix from version strings.

	Tests:
	    >>> _get_sanitized_version("1.2.15")
	    '1.2.15'
	    >>> _get_sanitized_version("1.2.15-dev12")
	    '1.2.15'
	"""
	if "-" in version_string:
		version_string = version_string[:version_string.find("-")]
	return version_string


def _get_base_from_version_tuple(version_tuple):
	"""
	Reduces version tuple to base version.

	Tests:

	    >>> _get_base_from_version_tuple(("1", "2", "15"))
	    ('1', '2', '15')
	    >>> _get_base_from_version_tuple(("1", "2", "15", "*", "dev12"))
	    ('1', '2', '15')
	"""

	base_version = []
	# A leading v is common in github release tags. Remove it.
	if version_tuple and version_tuple[0].lower() == "*v":
		version_tuple = version_tuple[1:]
	for part in version_tuple:
		if part.startswith("*"):
			break
		base_version.append(part)
	return tuple(base_version)


def _get_comparable_version_pkg_resources(version_string, force_base=True):
	import pkg_resources

	version = pkg_resources.parse_version(version_string)

	if force_base:
		if isinstance(version, tuple):
			# old setuptools
			version = _get_base_from_version_tuple(version)
		else:
			# new setuptools
			version = pkg_resources.parse_version(version.base_version)

	return version


def _get_comparable_version_semantic(version_string, force_base=True):
	import semantic_version

	version = semantic_version.Version.coerce(version_string, partial=False)

	if force_base:
		version_string = "{}.{}.{}".format(version.major, version.minor, version.patch)
		version = semantic_version.Version.coerce(version_string, partial=False)

	return version


def _get_sanitized_compare_type(compare_type, custom=None):
	if not compare_type in ("python", "python_unequal",
	                        "semantic", "semantic_unequal",
	                        "unequal", "custom") or compare_type == "custom" and custom is None:
		compare_type = "python"
	return compare_type


def _get_comparable_factory(compare_type, force_base=True):
	if compare_type in ("python", "python_unequal"):
		return lambda version: _get_comparable_version_pkg_resources(version, force_base=force_base)
	elif compare_type in ("semantic", "semantic_unequal"):
		return lambda version: _get_comparable_version_semantic(version, force_base=force_base)
	else:
		return lambda version: version


def _get_comparator(compare_type, custom=None):
	if compare_type in ("python", "semantic"):
		return lambda a, b: a >= b
	elif compare_type == "custom":
		return custom
	else:
		return lambda a, b: a == b


def _is_current(release_information, compare_type, custom=None, force_base=True):
	"""
	Checks if the provided release information indicates the version being the most current one.

	Tests:

	    >>> _is_current(dict(remote=dict(value=None))
	    True
	    >>> _is_current(dict(local=dict(value="1.2.15"), remote=dict(value="1.2.16")))
	    False
	    >>> _is_current(dict(local=dict(value="1.2.16dev1"), remote=dict(value="1.2.16dev2")))
	    True
	    >>> _is_current(dict(local=dict(value="1.2.16dev1"), remote=dict(value="1.2.16dev2")), force_base=False)
	    False
	    >>> _is_current(dict(local=dict(value="1.2.16dev3"), remote=dict(value="1.2.16dev2")), force_base=False)
	    True
	    >>> _is_current(dict(local=dict(value="1.2.16dev3"), remote=dict(value="1.2.16dev2")), force_base=False, compare_type="python_unequal")
	    False

	"""

	if release_information["remote"]["value"] is None:
		return True

	compare_type = _get_sanitized_compare_type(compare_type, custom=custom)
	comparable_factory = _get_comparable_factory(compare_type, force_base=force_base)
	comparator = _get_comparator(compare_type, custom=custom)

	sanitized_local = _get_sanitized_version(release_information["local"]["value"])
	sanitized_remote = _get_sanitized_version(release_information["remote"]["value"])

	try:
		return comparator(comparable_factory(sanitized_local),
		                  comparable_factory(sanitized_remote))
	except:
		logger.exception("Could not check if version is current due to an error, assuming it is")
		return True


def get_latest(target, check, custom_compare=None):
	if not "user" in check or not "repo" in check:
		raise ConfigurationInvalid("github_release update configuration for %s needs user and repo set" % target)

	current = check.get("current", None)
	include_prerelease = check.get("prerelease", False)
	prerelease_channel = check.get("prerelease_channel", None)
	force_base = check.get("force_base", True)
	compare_type = _get_sanitized_compare_type(check.get("release_compare", "python"),
	                                           custom=custom_compare)

	remote_name, remote_tag, release_notes = _get_latest_release(check["user"],
	                                                             check["repo"],
	                                                             compare_type,
	                                                             include_prerelease=include_prerelease,
	                                                             prerelease_channel=prerelease_channel,
	                                                             force_base=force_base)

	information =dict(
		local=dict(name=current, value=current),
		remote=dict(name=remote_name, value=remote_tag, release_notes=release_notes)
	)

	logger.debug("Target: %s, local: %s, remote: %s" % (target, current, remote_tag))

	return information, _is_current(information,
	                                compare_type,
	                                custom=custom_compare,
	                                force_base=force_base)
