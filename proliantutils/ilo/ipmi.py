# coding=utf-8

# Copyright 2012 Hewlett-Packard Development Company, L.P.
# Copyright (c) 2012 NTT DOCOMO, INC.
# Copyright 2014 International Business Machines Corporation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
NOTE THAT CERTAIN DISTROS MAY INSTALL openipmi BY DEFAULT, INSTEAD OF ipmitool,
WHICH PROVIDES DIFFERENT COMMAND-LINE OPTIONS AND *IS NOT SUPPORTED* BY THIS
DRIVER.
"""

import subprocess

from proliantutils import log

LOG = log.get_logger(__name__)

MIN_SUGGESTED_FW_REV = 2.3
DEFAULT_FW_REV = 2.1


def _exec_ipmitool(driver_info, command):
    """Execute the ipmitool command.

    This uses the lanplus interface to communicate with the BMC device driver.

    :param driver_info: the ipmitool parameters for accessing a node.
    :param command: the ipmitool command to be executed.

    """
    ipmi_cmd = ("ipmitool -H %(address)s"
                " -I lanplus -U %(user)s -P %(passwd)s %(cmd)s"
                % {'address': driver_info['address'],
                   'user': driver_info['username'],
                   'passwd': driver_info['password'],
                   'cmd': command})

    out = None
    try:
        process = subprocess.Popen(ipmi_cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True)
        out, err = process.communicate()
        LOG.debug(("IPMI Command output: %(out)s and "
                   "IPMI Command error: %(err)s and returncode: (code)s"),
                  {'out': out, 'err': err, 'code': process.returncode})
    except Exception:
        pass
    if out:
        return out.decode()
    else:
        return out


def get_ilo_version(ilo_fw_str):
    """Gets the float value of the firmware version

    Converts a string with major and minor numbers to a float value.

    :param ilo_fw_tup: String containing the major and minor versions
                       of the form <major>.<minor>
    :returns: float value constructed from major and minor numbers.
    """

    if not ilo_fw_str:
        return None

    try:
        major_minor_val = float(ilo_fw_str)
    except Exception:
        return None
    return major_minor_val


def get_nic_capacity(driver_info, ilo_fw):
    """Gets the FRU data to see if it is NIC data

    Gets the FRU data in loop from 0-255 FRU Ids
    and check if the returned data is NIC data. Couldn't
    find any easy way to detect if it is NIC data. We should't be
    hardcoding the FRU Id.

    :param driver_info: Contains the access credentials to access
                        the BMC.
    :param ilo_fw: a tuple containing major and minor versions of firmware
    :returns: the max capacity supported by the NIC adapter.
    """
    i = 0x0
    value = None
    ilo_fw_rev = get_ilo_version(ilo_fw) or DEFAULT_FW_REV

    # Note(vmud213): iLO firmware versions >= 2.3 support reading the FRU
    # information in a single call instead of iterating over each FRU id.
    if ilo_fw_rev < MIN_SUGGESTED_FW_REV:
        for i in range(0xff):
            # Note(vmud213): We can discard FRU ID's between 0x6e and 0xee
            # as they don't contain any NIC related information
            if (i < 0x6e) or (i > 0xee):
                cmd = "fru print %s" % hex(i)
                out = _exec_ipmitool(driver_info, cmd)
                if out and 'port' in out and 'Adapter' in out:
                    value = _parse_ipmi_nic_capacity(out)
                    if value is not None:
                        break
            else:
                continue
    else:
        cmd = "fru print"
        out = _exec_ipmitool(driver_info, cmd)
        if out:
            for line in out.split('\n'):
                if line and 'port' in line and 'Adapter' in line:
                    value = _parse_ipmi_nic_capacity(line)
                    if value is not None:
                        break
    return value


def _parse_ipmi_nic_capacity(nic_out):
    """Parse the FRU output for NIC capacity

    Parses the FRU output. Seraches for the key "Product Name"
    in FRU output and greps for maximum speed supported by the
    NIC adapter.

    :param nic_out: the FRU output for NIC adapter.
    :returns: the max capacity supported by the NIC adapter.

    """
    if (("Device not present" in nic_out)
       or ("Unknown FRU header" in nic_out) or not nic_out):
        return None

    capacity = None
    product_name = None
    data = nic_out.split('\n')
    for item in data:
        fields = item.split(':')
        if len(fields) > 1:
            first_field = fields[0].strip()
            if first_field == "Product Name":
                # Join the string back if the Product Name had some
                # ':' by any chance
                product_name = ':'.join(fields[1:])
                break

    if product_name:
        product_name_array = product_name.split(' ')
        for item in product_name_array:
            if 'Gb' in item:
                capacity_int = item.strip('Gb')
                if capacity_int.isdigit():
                    capacity = item

    return capacity
