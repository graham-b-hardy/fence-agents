#!@PYTHON@ -tt

# This agent uses Proxmox VE API
# Thanks to Frank Brendel (author of original perl fence_pve)
# for help with writing and testing this agent.

import sys
import json
import pycurl
import io
import atexit
import logging
sys.path.append("@FENCEAGENTSLIBDIR@")
from fencing import fail, fail_usage, EC_LOGIN_DENIED, atexit_handler, all_opt, check_input, process_input, show_docs, fence_action, run_delay

if sys.version_info[0] > 2: import urllib.parse as urllib
else: import urllib

def get_power_status(conn, options):
	del conn
	state = {"running" : "on", "stopped" : "off"}
	if options["--pve-node"] is None:
		nodes = send_cmd(options, "nodes")
		if type(nodes) is not dict or "data" not in nodes or type(nodes["data"]) is not list:
			return None
		for node in nodes["data"]: # lookup the node holding the vm
			if type(node) is not dict or "node" not in node:
				return None
			options["--pve-node"] = node["node"]
			status = get_power_status(None, options)
			if status is not None:
				logging.info("vm found on node: " + options["--pve-node"])
				break
			else:
				options["--pve-node"] = None
		return status
	else:
		cmd = "nodes/" + options["--pve-node"] + "/" + options["--vmtype"] +"/" + options["--plug"] + "/status/current"
		result = send_cmd(options, cmd)
		if type(result) is dict and "data" in result:
			if type(result["data"]) is dict and "status" in result["data"]:
				if result["data"]["status"] in state:
					return state[result["data"]["status"]]
		return None


def set_power_status(conn, options):
	del conn
	action = {
		'on' : "start",
		'off': "stop"
	}[options["--action"]]
	cmd = "nodes/" + options["--pve-node"] + "/" + options["--vmtype"] +"/" + options["--plug"] + "/status/" + action
	send_cmd(options, cmd, post={"skiplock":1})


def reboot_cycle(conn, options):
	del conn
	cmd = "nodes/" + options["--pve-node"] + "/" + options["--vmtype"] + "/" + options["--plug"] + "/status/reset"
	result = send_cmd(options, cmd, post={"skiplock":1})
	return type(result) is dict and "data" in result


def get_outlet_list(conn, options):
	del conn
	nodes = send_cmd(options, "nodes")
	outlets = dict()
	if type(nodes) is not dict or "data" not in nodes or type(nodes["data"]) is not list:
		return None
	for node in nodes["data"]:
		if type(node) is not dict or "node" not in node:
			return None
		vms = send_cmd(options, "nodes/" + node["node"] + "/" + options["--vmtype"])
		if type(vms) is not dict or "data" not in vms or type(vms["data"]) is not list:
			return None
		for vm in vms["data"]:
			outlets[vm["vmid"]] = [vm["name"], vm["status"]]
	return outlets


def get_ticket(options):
	post = {'username': options["--username"], 'password': options["--password"]}
	result = send_cmd(options, "access/ticket", post=post)
	if type(result) is dict and "data" in result:
		if type(result["data"]) is dict and "ticket" in result["data"] and "CSRFPreventionToken" in result["data"]:
			return {
				"ticket" : str("PVEAuthCookie=" + result["data"]["ticket"] + "; " + \
					"version=0; path=/; domain=" + options["--ip"] + \
					"; port=" + str(options["--ipport"]) + "; path_spec=0; secure=1; " + \
					"expires=7200; discard=0"),
				"CSRF_token" : str("CSRFPreventionToken: " + result["data"]["CSRFPreventionToken"])
				}
	return None


def send_cmd(options, cmd, post=None):
	url = options["url"] + cmd
	conn = pycurl.Curl()
	output_buffer = io.BytesIO()
	if logging.getLogger().getEffectiveLevel() < logging.WARNING:
		conn.setopt(pycurl.VERBOSE, True)
	conn.setopt(pycurl.HTTPGET, 1)
	conn.setopt(pycurl.URL, url.encode("ascii"))
	if "auth" in options and options["auth"] is not None:
		conn.setopt(pycurl.COOKIE, options["auth"]["ticket"])
		conn.setopt(pycurl.HTTPHEADER, [options["auth"]["CSRF_token"]])
	if post is not None:
		if "skiplock" in post:
			conn.setopt(conn.CUSTOMREQUEST, 'POST')
		else:
			conn.setopt(pycurl.POSTFIELDS, urllib.urlencode(post))
	conn.setopt(pycurl.WRITEFUNCTION, output_buffer.write)
	conn.setopt(pycurl.TIMEOUT, int(options["--shell-timeout"]))
	if "--ssl" in options or "--ssl-secure" in options:
		conn.setopt(pycurl.SSL_VERIFYPEER, 1)
		conn.setopt(pycurl.SSL_VERIFYHOST, 2)
	else:
		conn.setopt(pycurl.SSL_VERIFYPEER, 0)
		conn.setopt(pycurl.SSL_VERIFYHOST, 0)

	logging.debug("URL: " + url)

	try:
		conn.perform()
		result = output_buffer.getvalue().decode()

		logging.debug("RESULT [" + str(conn.getinfo(pycurl.RESPONSE_CODE)) + \
			"]: " + result)
		conn.close()

		return json.loads(result)
	except pycurl.error:
		logging.error("Connection failed")
	except:
		logging.error("Cannot parse json")
	return None


def main():
	atexit.register(atexit_handler)

	all_opt["pve_node_auto"] = {
		"getopt" : "A",
		"longopt" : "pve-node-auto",
		"help" : "-A, --pve-node-auto            "
			"Automatically select proxmox node",
		"required" : "0",
		"shortdesc" : "Automatically select proxmox node. "
			"(This option overrides --pve-node)",
		"type": "boolean",
		"order": 2
	}
	all_opt["pve_node"] = {
		"getopt" : "N:",
		"longopt" : "pve-node",
		"help" : "-N, --pve-node=[node_name]     "
			"Proxmox node name on which machine is located",
		"required" : "0",
		"shortdesc" : "Proxmox node name on which machine is located. "
			"(Must be specified if not using --pve-node-auto)",
		"order": 2
	}
	all_opt["node_name"] = {
		"getopt" : ":",
		"longopt" : "nodename",
		"help" : "--nodename                     "
			"Replaced by --pve-node",
		"required" : "0",
		"shortdesc" : "Replaced by --pve-node",
		"order": 3
	}
	all_opt["vmtype"] = {
		"getopt" : ":",
		"longopt" : "vmtype",
		"default" : "qemu",
		"help" : "--vmtype                       "
			"Virtual machine type lxc or qemu (default: qemu)",
		"required" : "1",
		"shortdesc" : "Virtual machine type lxc or qemu. "
			"(Default: qemu)",
		"order": 2
	}

	device_opt = ["ipaddr", "login", "passwd", "web", "port", "pve_node", "pve_node_auto", "node_name", "vmtype", "method"]

	all_opt["login"]["required"] = "0"
	all_opt["login"]["default"] = "root@pam"
	all_opt["ipport"]["default"] = "8006"
	all_opt["port"]["shortdesc"] = "Id of the virtual machine."
	all_opt["ipaddr"]["shortdesc"] = "IP Address or Hostname of a node " +\
		"within the Proxmox cluster."

	options = check_input(device_opt, process_input(device_opt))
	docs = {}
	docs["shortdesc"] = "Fencing agent for the Proxmox Virtual Environment"
	docs["longdesc"] = "The fence_pve agent can be used to fence virtual \
machines acting as nodes in a virtualized cluster."
	docs["vendorurl"] = "http://www.proxmox.com/"

	show_docs(options, docs)

	run_delay(options)

	if "--pve-node-auto" in options:
		# Force pve-node to None to allow autodiscovery
		options["--pve-node"] = None
	elif "--pve-node" in options and options["--pve-node"]:
		# Leave pve-node alone
		pass
	elif "--nodename" in options and options["--nodename"]:
		# map nodename into pve-node to support legacy implementations
		options["--pve-node"] = options["--nodename"]
	else:
		fail_usage("At least one of pve-node-auto or pve-node must be supplied")


	if options["--vmtype"] != "qemu":
		# For vmtypes other than qemu, only the onoff method is valid
		options["--method"] = "onoff"

	options["url"] = "https://" + options["--ip"] + ":" + str(options["--ipport"]) + "/api2/json/"

	options["auth"] = get_ticket(options)
	if options["auth"] is None:
		fail(EC_LOGIN_DENIED)

	# Workaround for unsupported API call on some Proxmox hosts
	outlets = get_outlet_list(None, options)        # Unsupported API-Call will result in value: None
	if outlets is None:
		result = fence_action(None, options, set_power_status, get_power_status, None, reboot_cycle)
		sys.exit(result)

	result = fence_action(None, options, set_power_status, get_power_status, get_outlet_list, reboot_cycle)

	sys.exit(result)

if __name__ == "__main__":
	main()
