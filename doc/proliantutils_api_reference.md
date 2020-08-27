# Proliantutils documentation

Introduction
============

**Proliantutils** is a set of python utility libraries for interfacing and managing various components
(like iLO, HPSSA) for HPE iLO-based Servers. This library uses Redfish to interact with Gen10 servers
and RIBCL/RIS to interact with Gen8 and Gen9 servers. A subset of proliantutils can be used to discover
server properties (aka
**Discovery Engine**).

Please use [launchpad](https://bugs.launchpad.net/proliantutils) to report bugs and ask questions.

Installation
============

Install the module from [PyPI](https://pypi.python.org/pypi/proliantutils). If you are using Ironic,
install the module on Ironic conductor node:

```$ pip install proliantutils```

**Some GNU/Linux distributions provide *python-proliantutils* package.**

Supported Operations
====================

Creating an IloClient object for interfacing with the iLO, use *IloClient* object:

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_host_power_status()

   'OFF'
```

**For operations supported on the client object, please refer *proliantutils.ilo.operations*.**

get_all_licenses()
------------------

Retrieves license type, key, installation date, etc.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_all_licenses()

   {'LICENSE_TIER': 'ADV', 'LICENSE_INSTALL_DATE': '10 May 2019',
   'LICENSE_CLASS': 'FQL', 'LICENSE_TYPE': 'iLO Advanced',
   'LICENSE_KEY': 'YOUR_LICENSE_KEY', 'LICENSE_STATE': 'unconfirmed'}
```

get_product_name()
------------------

Retrieves the model name of the queried server.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_product_name()

   u'ProLiant DL360 Gen10'
```

get_host_power_status()
----------------------

Retrieves the power status of the server.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_host_power_status()

   'ON'
```

get_http_boot_url()
-------------------

Retrieves the http boot url.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_http_boot_url()

   u'http://10.10.1.30:8081/startup.nsh'
```

set_http_boot_url(url)
----------------------

Set the url to the UefiShellStartupUrl. Takes url for http boot as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.set_http_boot_url("http://10.10.1.30:8081/startup.nsh")
```

set_iscsi_info(target_name, lun, ip_address, port='3260', auth_method=None, username=None, password=None, macs=[])
------------------------------------------------------------------------------------------------------------------

Sets iscsi details of the system in uefi boot mode.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.set_iscsi_info('iqn.2011-07.com:example:123', '1', '10.10.1.23', '3260', 'CHAP', 'user', 'password')
```

unset_iscsi_info(macs=[])
-------------------------

Disable iscsi boot option of the system in uefi boot mode. Takes a list of target MAC addresses as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.unset_iscsi_info(['98:f2:b3:ee:f4:00'])
```

get_iscsi_initiator_info()
--------------------------

Retrieves iSCSI initiator information of iLO.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_iscsi_initiator_info()

   'iqn.2015-02.com.hpe:uefi-U32-G393NR9113'
```

set_iscsi_initiator_info(initiator_iqn)
---------------------------------------

Sets iSCSI initiator information of iLO. Takes an initiator iqn for iLO as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.set_iscsi_initiator_info('iqn.2015-02.com.hpe:uefi-U32-G393NR9113')
```

get_one_time_boot()
-------------------

Retrieves the current setting for the one time boot.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_one_time_boot()

   'Normal'
```

get_vm_status(device='FLOPPY')
------------------------------

Retrieves the virtual media drive status like url, is connected, etc. Takes virtual media *device* as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_vm_status('FLOPPY')

   {'WRITE_PROTECT': 'NO', 'VM_APPLET': 'DISCONNECTED', 'IMAGE_URL':
   u'', 'BOOT_OPTION': 'NO_BOOT', 'DEVICE': 'FLOPPY', 'IMAGE_INSERTED':
   'NO'}
```

reset_server()
--------------

Resets the server.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.reset_server()
```

press_pwr_btn()
---------------

Simulates a physical press of the server power button.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_host_power_status()

   u'ON'

   >>> ilo_client.press_pwr_btn()

   >>> ilo_client.get_host_power_status()

   u'OFF'
```

hold_pwr_btn()
--------------

Simulate a physical press and hold of the server power button.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_host_power_status()

   u'ON'

   >>> ilo_client.hold_pwr_btn()

   >>> ilo_client.get_host_power_status()

   u'OFF'
```

set_host_power(power)
---------------------

Toggles the power button of the server. Takes power status as argument. The power status values can be ‘ON’ or ‘OFF’.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.set_host_power('ON')

   >>> ilo_client.get_host_power_status()

   u'ON'

   >>> ilo_client.set_host_power('OFF')

   >>> ilo_client.get_host_power_status()

   u'OFF'
```

set_one_time_boot(value)
------------------------

Configures the server for a single boot from a specific device. Takes a boot device value as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_one_time_boot()

   'Normal'

   >>> ilo_client.set_one_time_boot('CDROM')

   >>> ilo_client.get_one_time_boot()

   'CDROM'
```

insert_virtual_media(url, device=’FLOPPY’)
------------------------------------------

Notifies iLO of the location of a virtual media diskette image. Takes the virtual media url and device as arguments.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.insert_virtual_media(url='http://172.17.1.41:8001/rhel_8_1.iso', device='FLOPPY')

   >>> ilo_client.get_vm_status('FLOPPY')

   {'WRITE_PROTECT': 'YES', 'VM_APPLET': 'CONNECTED', 'IMAGE_URL':
    u'http://172.17.1.41:8001/rhel_8_1.iso', 'BOOT_OPTION':
    'BOOT_ALWAYS', 'DEVICE': 'FLOPPY', 'IMAGE_INSERTED': 'YES'}
```

eject_virtual_media(device=’FLOPPY’)
------------------------------------

Ejects the Virtual Media image if one is inserted. Takes virtual media device as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.eject_virtual_media(device='FLOPPY')

   >>> ilo_client.get_vm_status('FLOPPY')

   {'WRITE_PROTECT': 'YES', 'VM_APPLET': 'DISCONNECTED', 'IMAGE_URL':
    u'', 'BOOT_OPTION': 'NO_BOOT', 'DEVICE': 'FLOPPY', 'IMAGE_INSERTED':
    'NO'}
```

set_vm_status(device=’FLOPPY’, boot_option=’BOOT_ONCE’, write_protect=’YES’)
----------------------------------------------------------------------------

Sets the Virtual Media drive status and allows the boot options for booting from the virtual media.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.set_vm_status(device='FLOPPY', boot_option='BOOT_ONCE', write_protect='YES')
```

get_current_boot_mode()
-----------------------

Retrieves the current boot mode settings.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_current_boot_mode()

   u'UEFI'
```

get_pending_boot_mode()
-----------------------

Retrieves the pending boot mode settings

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_pending_boot_mode()

   u'UEFI'
```

get_supported_boot_mode()
-------------------------

Lists all supported boot modes

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_supported_boot_mode()

   'legacy bios and uefi'
```

set_pending_boot_mode(value)
----------------------------

Sets the boot mode of the system for next boot. Takes boot mode as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.set_pending_boot_mode('UEFI')

   >>> ilo_client.get_pending_boot_mode()

   u'UEFI'
```

get_persistent_boot_device()
----------------------------

Retrieves the current persistent boot device set for the host

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_persistent_boot_device()

   'CDROM'
```

update_persistent_boot(device_type=[])
--------------------------------------

Updates persistent boot based on the boot mode. Takes list of boot devices as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.update_persistent_boot(['cdrom'])
```

get_secure_boot_mode()
----------------------

Retrieves whether secure boot is enabled or not.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_secure_boot_mode()

   False
```

set_secure_boot_mode(secure_boot_enable)
----------------------------------------

Enables/Disables secure boot on the server. Takes boolean value as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_secure_boot_mode()

   False

   >>> ilo_client.set_secure_boot_mode(True)

   >>> ilo_client.get_secure_boot_mode()

   True
```

reset_secure_boot_keys()
------------------------

Resets secure boot keys to manufacturing defaults.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.reset_secure_boot_keys()
```

clear_secure_boot_keys()
------------------------

Resets all keys.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.clear_secure_boot_keys()
```

reset_ilo_credential(password)
------------------------------

Resets the iLO password.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.reset_ilo_credential('Pa5sword')
```

reset_ilo()
-----------

Resets the server iLO.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.reset_ilo()
```

reset_bios_to_default()
-----------------------

Resets the BIOS settings to default values.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.reset_bios_to_default()
```

get_host_uuid()
---------------

Retrieves the host UUID of the server

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_host_uuid()

   ('ProLiant DL180 Gen9', '35343537-3432-4753-4836-34305752394B')
```

get_host_health_data(data=None)
-------------------------------

Returns the dictionary containing the embedded health data. Takes *data* to be retrieved as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_host_health_data()

   {'VERSION': '2.23', 'RESPONSE': {'STATUS': '0x0000', 'MESSAGE': 'No error'}, ...... }
```

get_host_health_present_power_reading(data=None)
------------------------------------------------

Returns the power consumption of the server. Takes *data* to be retrieved as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_host_health_present_power_reading()

   '0 Watts'
```

get_host_health_power_supplies(data=None)
-----------------------------------------

Returns the health information of power supplies. Takes *data* to be retrieved as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_host_health_power_supplies()

   [{'STATUS': {'VALUE': 'Unknown'}, 'CAPACITY': {'VALUE': 'N/A'}, 'PDS':
   {'VALUE': 'Other'}, 'LABEL': {'VALUE': 'Power Supply 1'},
   'HOTPLUG_CAPABLE': {'VALUE': 'No'}, 'SPARE': {'VALUE': 'N/A'},
   'SERIAL_NUMBER': {'VALUE': 'N/A'}, 'MODEL': {'VALUE': 'N/A'},
   'FIRMWARE_VERSION': {'VALUE': 'N/A'}, 'PRESENT': {'VALUE': 'No'}}]
```

get_host_health_fan_sensors(data=None)
--------------------------------------

Returns the health information from Fan Sensors. Takes *data* to be retrieved as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_host_health_fan_sensors()

   [{'STATUS': {'VALUE': 'Other'}, 'SPEED': {'UNIT': 'Percentage', 'VALUE':
   '0'}, 'ZONE': {'VALUE': 'System'}, 'LABEL': {'VALUE': 'Fan 1'}},
   {'STATUS': {'VALUE': 'Other'}, 'SPEED': {'UNIT': 'Percentage', 'VALUE':
   '0'}, 'ZONE': {'VALUE': 'System'}, 'LABEL': {'VALUE': 'Fan 2'}},
   {'STATUS': {'VALUE': 'Other'}, 'SPEED': {'UNIT': 'Percentage', 'VALUE':
   '0'}, 'ZONE': {'VALUE': 'System'}, 'LABEL': {'VALUE': 'Fan 3'}},
   {'STATUS': {'VALUE': 'Other'}, 'SPEED': {'UNIT': 'Percentage', 'VALUE':
   '0'}, 'ZONE': {'VALUE': 'System'}, 'LABEL': {'VALUE': 'Fan 4'}},
   {'STATUS': {'VALUE': 'Other'}, 'SPEED': {'UNIT': 'Percentage', 'VALUE':
   '0'}, 'ZONE': {'VALUE': 'System'}, 'LABEL': {'VALUE': 'Fan 5'}}]
```

get_host_health_temperature_sensors(data=None)
----------------------------------------------

Returns the health information from Temperature Sensors. Takes *data* to be retrieved as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_host_health_temperature_sensors()

   [{'LABEL': {'VALUE': '01-CPU 1'}, 'LOCATION': {'VALUE': 'CPU'}, 'STATUS': {'VALUE':
   'Not Installed'}, 'CURRENTREADING': {'VALUE': 'N/A'}, 'CAUTION': {'VALUE': 'N/A'},
   'CRITICAL': {'VALUE': 'N/A'}},,
   {'LABEL': {'VALUE': '02-CPU 1'}, 'LOCATION': {'VALUE': 'CPU'}, 'STATUS': {'VALUE':
   'OK'}, 'CURRENTREADING': {'VALUE': '40', 'UNIT': 'Celsius'}, 'CAUTION': {'VALUE':
   '70', 'UNIT': 'Celsius'}, 'CRITICAL': {'VALUE': 'N/A'}},
   {'LABEL': {'VALUE': '03-CPU 2'}, 'LOCATION': {'VALUE': 'CPU'}, 'STATUS': {'VALUE':
   'Not Installed'}, 'CURRENTREADING': {'VALUE': 'N/A'}, 'CAUTION': {'VALUE': 'N/A'},
   'CRITICAL': {'VALUE': 'N/A'}},
   {'LABEL': {'VALUE': '04-CPU 2'}, 'LOCATION': {'VALUE': 'CPU'}, 'STATUS': {'VALUE':
   'Not Installed'}, 'CURRENTREADING': {'VALUE': 'N/A'}, 'CAUTION': {'VALUE': 'N/A'},
   'CRITICAL': {'VALUE': 'N/A'}}]
```

get_host_health_at_a_glance(data=None)
--------------------------------------

Returns health at a glance report. Takes *data* to be retrieved as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_host_health_at_a_glance()

    {'TEMPERATURE': {'STATUS': 'Not Installed'}, 'BATTERY': {'STATUS': 'Not
    Installed'}, 'STORAGE': {'STATUS': 'OK'}, 'FANS': {'STATUS': 'Not
    Installed'}, 'BIOS_HARDWARE': {'STATUS': 'OK'}, 'MEMORY': {'STATUS':
    'Other'}, 'POWER_SUPPLIES': {'STATUS': 'Not Installed'}, 'PROCESSOR':
    {'STATUS': 'OK'}, 'NETWORK': {'STATUS': 'OK'}}
```

get_host_power_readings()
-------------------------

Returns the host power reading.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_host_power_readings()

   {'MAXIMUM_POWER_READING': {'UNIT': 'Watts', 'VALUE': '243'},
   'MINIMUM_POWER_READING': {'UNIT': 'Watts', 'VALUE': '136'},
   'PRESENT_POWER_READING': {'UNIT': 'Watts', 'VALUE': '224'},
   'AVERAGE_POWER_READING': {'UNIT': 'Watts', 'VALUE': '162'}}
```

get_essential_properties()
--------------------------

Returns the essential scheduling properties.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_essential_properties()

   {'macs': {u'Port 6': u'80:30:e0:2d:3f:31', u'Port 5':
   u'80:30:e0:2d:3f:30'}, 'properties': {'memory_mb': 65536, 'cpu_arch':
   'x86', 'local_gb': 278, 'cpus': 48}}
```

get_server_capabilities()
-------------------------

Returns hardware properties which can be used for scheduling.

This method can discover the following properties:

  * **ilo_firmware_version**: iLO firmware version

  *  **rom_firmware_version**: ROM firmware version

  *  **secure_boot**: secure boot is supported or not. The possible values
     are ‘true’ or ‘false’. The value is returned as ‘true’ if secure boot
     is supported by the server.

  *  **server_model**: server model

  *  **pci_gpu_devices**: number of gpu devices connected to the bare
     metal.

  *  **nic_capacity**: the max speed of the embedded NIC adapter.

  *  **sriov_enabled**: true, if server has the SRIOV supporting NIC.

  *  **has_rotational**: true, if server has HDD disk.

  *  **has_ssd**: true, if server has SSD disk.

  *  **has_nvme_ssd**: true, if server has NVME SSD disk.

  *  **cpu_vt**: true, if server supports cpu virtualization.

  *  **hardware_supports_raid**: true, if RAID can be configured on the
     server using RAID controller.

  *  **nvdimm_n**: true, if server has NVDIMM_N type of persistent memory.

  *  **persistent_memory**: true, if server has persistent memory.

  *  **logical_nvdimm_n**: true, if server has logical NVDIMM_N
     configured.

  * **boot_mode_bios**: true, if server boot mode is BIOS.

  * **boot_mode_uefi**: true, if server boot mode is UEFI.

  * **iscsi_boot**: true, if server supported UEFI iSCSI boot.

  *  **rotational_drive_<speed>_rpm**: The capabilities
     *rotational_drive_4800_rpm*, *rotational_drive_5400_rpm*,
     *rotational_drive_7200_rpm*, *rotational_drive_10000_rpm* and
     *rotational_drive_15000_rpm* are set to true if the server has HDD
     drives with speed of 4800, 5400, 7200, 10000 and 15000 rpm
     respectively.

  *  **logical_raid_level_<raid_level>**: The capabilities
     *logical_raid_level_0*, *logical_raid_level_1*,
     *logical_raid_level_2*, *logical_raid_level_5*,
     *logical_raid_level_6*, *logical_raid_level_10*,
     *logical_raid_level_50* and *logical_raid_level_60* are set to
     true if any of the raid levels among 0, 1, 2, 5, 6, 10, 50 and 60 are
     configured on the system.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_server_capabilities()

   {'logical_raid_level_0': 'true', 'has_rotational': 'true',
   'rom_firmware_version': u'U32 v2.02 (03/19/2019)',
   'hardware_supports_raid': 'true', 'cpu_vt': 'true',
   'sriov_enabled': 'true', 'boot_mode_bios': 'true',
   'trusted_boot': 'true', 'boot_mode_uefi': 'true',
   'server_model': u'ProLiant DL360 Gen10', 'nic_capacity': '16Gb',
   'pci_gpu_devices': 1, 'ilo_firmware_version': u'iLO 5 v1.40',
   'secure_boot': 'true', 'drive_rotational_10000_rpm': 'true',
   'iscsi_boot': 'true'}
```

activate_license(key)
---------------------

Activates iLO license. Takes license key as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.activate_license('YOUR_LICENSE_KEY')
```

update_firmware(firmware_url, component_type)
---------------------------------------------

Updates the given firmware on the server. Takes location of firmware file and the component to be applied to as arguments.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.update_firmware('http://172.17.1.41/ilo_firmware', 'ilo')
```

inject_nmi()
------------

Injects an NMI (Non Maskable Interrupt) for a node immediately.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.inject_nmi()
```

get_host_post_state()
---------------------

Returns the current state of system POST.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_host_post_state()

   'InPostDiscoveryComplete'
```

get_current_bios_settings(only_allowed_settings=False)
------------------------------------------------------

Returns current BIOS settings.

When *only_allowed_settings* is set to True, only allowed BIOS settings are returned.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_current_bios_settings(only_allowed_settings=True)

   {'PowerRegulator': u'DynamicPowerSavings', 'AdvancedMemProtection':
   u'FastFaultTolerantADDDC', 'DynamicPowerCapping': u'Disabled',
   'BootOrderPolicy': u'RetryIndefinitely', 'Sriov': u'Enabled',
   'AutoPowerOn': u'RestoreLastState', 'IntelProcVtd': u'Enabled',
   'ProcVirtualization': u'Enabled', 'ThermalShutdown': u'Enabled',
   'IntelTxt': u'Disabled', 'SecureBootStatus': u'Disabled',
   'WorkloadProfile': u'GeneralPowerEfficientCompute',
   'IntelPerfMonitoring': u'Disabled', 'TpmType': u'Tpm20',
   'UefiOptimizedBoot': u'Enabled', 'ThermalConfig': u'OptimalCooling',
   'ProcAes': u'Enabled', 'BootMode': u'Uefi', 'ProcTurbo': u'Enabled',
   'IntelligentProvisioning': u'Enabled', 'ProcHyperthreading': u'Enabled',
   'TpmState': u'PresentEnabled', 'CollabPowerControl': u'Enabled'}
```

When *only_allowed_settings* is set to False, all the BIOS settings supported by iLO are returned.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_current_bios_settings(only_allowed_settings=False)

   {'AcpiHpet': 'Enabled', 'AcpiRootBridgePxm': 'Enabled', 'AcpiSlit': 'Enabled',
   'AdjSecPrefetch': 'Enabled', 'AdminEmail': '', 'AdminName': '',
   'AdminOtherInfo': '', 'AdminPhone': '', 'AdvCrashDumpMode': 'Disabled',
   'AdvancedMemProtection': 'FastFaultTolerantADDDC', 'AsrStatus': 'Enabled',
   'AsrTimeoutMinutes': 'Timeout10', 'AssetTagProtection': 'Unlocked',
   'AutoPowerOn': 'RestoreLastState', 'BootMode': 'LegacyBios', 'BootOrderPolicy':
   'RetryIndefinitely', 'ChannelInterleaving': 'Enabled', 'CollabPowerControl':
   'Enabled', 'ConsistentDevNaming': 'LomsAndSlots', 'CustomPostMessage': '',
   'DaylightSavingsTime': 'Disabled', 'DcuIpPrefetcher': 'Enabled',
   'DcuStreamPrefetcher': 'Enabled', 'Dhcpv4': 'Enabled', 'DynamicPowerCapping':
   'Disabled', 'EmbNicEnable': 'Auto', 'EmbNicLinkSpeed': 'Auto',
   'EmbNicPCIeOptionROM': 'Enabled', 'EmbSas1Aspm': 'Disabled', 'EmbSas1Boot':
   'TwentyFourTargets', 'EmbSas1Enable': 'Auto', 'EmbSas1LinkSpeed': 'Auto',
   'EmbSas1PcieOptionROM': 'Enabled', 'EmbSata1Aspm': 'Disabled', 'EmbSata2Aspm':
   'Disabled', 'EmbVideoConnection': 'Auto', 'EmbeddedDiagnostics': 'Enabled',
   'EmbeddedSata': 'Ahci', 'EmbeddedSerialPort': 'Com2Irq3', 'EmbeddedUefiShell':
   'Enabled', 'EmsConsole': 'Disabled', 'EnabledCoresPerProc': 0,
   'EnergyEfficientTurbo': 'Enabled', 'EnergyPerfBias': 'BalancedPerf',
   'EraseUserDefaults': 'No', 'ExtendedAmbientTemp': 'Disabled', 'ExtendedMemTest':
   'Disabled', 'F11BootMenu': 'Enabled', 'FCScanPolicy': 'CardConfig',
   'FanFailPolicy': 'Shutdown', 'FanInstallReq': 'EnableMessaging', 'FlexLom1Aspm':
   'Disabled', 'HttpSupport': 'Auto', 'HwPrefetcher': 'Enabled',
   'IODCConfiguration': 'Auto', 'IntelDmiLinkFreq': 'Auto', 'IntelNicDmaChannels':
   'Enabled', 'IntelPerfMonitoring': 'Disabled', 'IntelProcVtd': 'Enabled',
   'IntelligentProvisioning': 'Enabled', 'InternalSDCardSlot': 'Enabled',
   'Ipv4Address': '0.0.0.0', 'Ipv4Gateway': '0.0.0.0', 'Ipv4PrimaryDNS': '0.0.0.0',
   'Ipv4SecondaryDNS': '0.0.0.0', 'Ipv4SubnetMask': '0.0.0.0', 'Ipv6Address': '::',
   'Ipv6ConfigPolicy': 'Automatic', 'Ipv6Duid': 'Auto', 'Ipv6Gateway': '::',
   'Ipv6PrimaryDNS': '::', 'Ipv6SecondaryDNS': '::', 'LLCDeadLineAllocation':
   'Enabled', 'LlcPrefetch': 'Disabled', 'LocalRemoteThreshold': 'Auto',
   'MaxMemBusFreqMHz': 'Auto', 'MaxPcieSpeed': 'PerPortCtrl', 'MemClearWarmReset':
   'Disabled', 'MemFastTraining': 'Enabled', 'MemMirrorMode': 'Full',
   'MemPatrolScrubbing': 'Enabled', 'MemRefreshRate': 'Refreshx1',
   'MemoryControllerInterleaving': 'Auto', 'MemoryRemap': 'NoAction',
   'MinProcIdlePkgState': 'C6Retention', 'MinProcIdlePower': 'C6',
   'MixedPowerSupplyReporting': 'Enabled', 'NetworkBootRetry': 'Enabled',
   'NetworkBootRetryCount': 20, 'NicBoot1': 'NetworkBoot', 'NicBoot2': 'Disabled',
   'NicBoot3': 'Disabled', 'NicBoot4': 'Disabled', 'NodeInterleaving': 'Disabled',
   'NumaGroupSizeOpt': 'Flat', 'NvmeOptionRom': 'Enabled',
   'OpportunisticSelfRefresh': 'Disabled', 'PciPeerToPeerSerialization':
   'Disabled', 'PciResourcePadding': 'Normal', 'PersistentMemBackupPowerPolicy':
   'WaitForBackupPower', 'PostBootProgress': 'Disabled', 'PostDiscoveryMode':
   'Auto', 'PostF1Prompt': 'Delayed20Sec', 'PostVideoSupport': 'DisplayAll',
   'PowerButton': 'Enabled', 'PowerOnDelay': 'NoDelay', 'PowerRegulator':
   'DynamicPowerSavings', 'PreBootNetwork': 'Auto', 'PrebootNetworkEnvPolicy':
   'Auto', 'PrebootNetworkProxy': '', 'ProcAes': 'Enabled', 'ProcHyperthreading':
   'Enabled', 'ProcTurbo': 'Enabled', 'ProcVirtualization': 'Enabled',
   'ProcX2Apic': 'Enabled', 'ProcessorConfigTDPLevel': 'Normal',
   'ProcessorJitterControl': 'Disabled', 'ProcessorJitterControlFrequency': 0,
   'ProcessorJitterControlOptimization': 'ZeroLatency', 'ProductId': '868703-B21',
   'RedundantPowerSupply': 'BalancedMode', 'RemovableFlashBootSeq':
   'ExternalKeysFirst', 'RestoreDefaults': 'No', 'RestoreManufacturingDefaults':
   'No', 'RomSelection': 'CurrentRom', 'SataSecureErase': 'Disabled',
   'SaveUserDefaults': 'No', 'SecStartBackupImage': 'Disabled', 'SecureBootStatus':
   'Disabled', 'SerialConsoleBaudRate': 'BaudRate115200', 'SerialConsoleEmulation':
   'Vt100Plus', 'SerialConsolePort': 'Auto', 'SerialNumber': 'SGH744YPVS',
   'ServerAssetTag': '', 'ServerConfigLockStatus': 'Disabled', 'ServerName':
   'localhost', 'ServerOtherInfo': '', 'ServerPrimaryOs': '', 'ServiceEmail': '',
   'ServiceName': '', 'ServiceOtherInfo': '', 'ServicePhone': '',
   'SetupBrowserSelection': 'Auto', 'Sriov': 'Enabled', 'StaleAtoS': 'Disabled',
   'SubNumaClustering': 'Disabled', 'ThermalConfig': 'OptimalCooling',
   'ThermalShutdown': 'Enabled', 'TimeFormat': 'Utc', 'TimeZone': 'Utc0',
   'TpmChipId': 'None', 'TpmFips': 'NotSpecified', 'TpmState': 'NotPresent',
   'TpmType': 'NoTpm', 'UefiOptimizedBoot': 'Disabled', 'UefiSerialDebugLevel':
   'Disabled', 'UefiShellBootOrder': 'Disabled', 'UefiShellScriptVerification':
   'Disabled', 'UefiShellStartup': 'Disabled', 'UefiShellStartupLocation': 'Auto',
   'UefiShellStartupUrl': '', 'UefiShellStartupUrlFromDhcp': 'Disabled',
   'UncoreFreqScaling': 'Auto', 'UrlBootFile': '', 'UrlBootFile2': '',
   'UrlBootFile3': '', 'UrlBootFile4': '', 'UsbBoot': 'Enabled', 'UsbControl':
   'UsbEnabled', 'UserDefaultsState': 'Disabled', 'UtilityLang': 'English',
   'VirtualInstallDisk': 'Disabled', 'VirtualSerialPort': 'Com1Irq4',
   'VlanControl': 'Disabled', 'VlanId': 0, 'VlanPriority': 0, 'WakeOnLan':
   'Enabled', 'WorkloadProfile': 'GeneralPowerEfficientCompute', 'XptPrefetcher':
   'Auto', 'iSCSIPolicy': 'SoftwareInitiator'}
```

get_pending_bios_settings(only_allowed_settings=False)
------------------------------------------------------

Returns pending BIOS settings.

When *only_allowed_settings* is set to True, only allowed BIOS settings are returned.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_pending_bios_settings(True)

   {'PowerRegulator': u'DynamicPowerSavings', 'AdvancedMemProtection':
   u'FastFaultTolerantADDDC', 'DynamicPowerCapping': u'Disabled',
   'BootOrderPolicy': u'RetryIndefinitely', 'Sriov': u'Enabled',
   'AutoPowerOn': u'RestoreLastState', 'IntelProcVtd': u'Enabled',
   'ProcVirtualization': u'Enabled', 'ThermalShutdown': u'Enabled',
   'IntelTxt': u'Disabled', 'SecureBootStatus': u'Disabled',
   'WorkloadProfile': u'GeneralPowerEfficientCompute',
   'IntelPerfMonitoring': u'Disabled', 'TpmType': u'Tpm20',
   'UefiOptimizedBoot': u'Enabled', 'ThermalConfig': u'OptimalCooling',
   'ProcAes': u'Enabled', 'BootMode': u'Uefi', 'ProcTurbo': u'Enabled',
   'IntelligentProvisioning': u'Enabled', 'ProcHyperthreading': u'Enabled',
   'TpmState': u'PresentEnabled', 'CollabPowerControl': u'Enabled'}
```

When *only_allowed_settings* is set to False, all the BIOS settings supported by iLO are returned.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_pending_bios_settings(False)

   {'AcpiHpet': 'Enabled', 'AcpiRootBridgePxm': 'Enabled', 'AcpiSlit': 'Enabled',
   'AdjSecPrefetch': 'Enabled', 'AdminEmail': '', 'AdminName': '',
   'AdminOtherInfo': '', 'AdminPhone': '', 'AdvCrashDumpMode': 'Disabled',
   'AdvancedMemProtection': 'FastFaultTolerantADDDC', 'AsrStatus': 'Enabled',
   'AsrTimeoutMinutes': 'Timeout10', 'AssetTagProtection': 'Unlocked',
   'AutoPowerOn': 'RestoreLastState', 'BootMode': 'LegacyBios', 'BootOrderPolicy':
   'RetryIndefinitely', 'ChannelInterleaving': 'Enabled', 'CollabPowerControl':
   'Enabled', 'ConsistentDevNaming': 'LomsAndSlots', 'CustomPostMessage': '',
   'DaylightSavingsTime': 'Disabled', 'DcuIpPrefetcher': 'Enabled',
   'DcuStreamPrefetcher': 'Enabled', 'Dhcpv4': 'Enabled', 'DynamicPowerCapping':
   'Disabled', 'EmbNicEnable': 'Auto', 'EmbNicLinkSpeed': 'Auto',
   'EmbNicPCIeOptionROM': 'Enabled', 'EmbSas1Aspm': 'Disabled', 'EmbSas1Boot':
   'TwentyFourTargets', 'EmbSas1Enable': 'Auto', 'EmbSas1LinkSpeed': 'Auto',
   'EmbSas1PcieOptionROM': 'Enabled', 'EmbSata1Aspm': 'Disabled', 'EmbSata2Aspm':
   'Disabled', 'EmbVideoConnection': 'Auto', 'EmbeddedDiagnostics': 'Enabled',
   'EmbeddedSata': 'Ahci', 'EmbeddedSerialPort': 'Com2Irq3', 'EmbeddedUefiShell':
   'Enabled', 'EmsConsole': 'Disabled', 'EnabledCoresPerProc': 0,
   'EnergyEfficientTurbo': 'Enabled', 'EnergyPerfBias': 'BalancedPerf',
   'EraseUserDefaults': 'No', 'ExtendedAmbientTemp': 'Disabled', 'ExtendedMemTest':
   'Disabled', 'F11BootMenu': 'Enabled', 'FCScanPolicy': 'CardConfig',
   'FanFailPolicy': 'Shutdown', 'FanInstallReq': 'EnableMessaging', 'FlexLom1Aspm':
   'Disabled', 'HttpSupport': 'Auto', 'HwPrefetcher': 'Enabled',
   'IODCConfiguration': 'Auto', 'IntelDmiLinkFreq': 'Auto', 'IntelNicDmaChannels':
   'Enabled', 'IntelPerfMonitoring': 'Disabled', 'IntelProcVtd': 'Enabled',
   'IntelligentProvisioning': 'Enabled', 'InternalSDCardSlot': 'Enabled',
   'Ipv4Address': '0.0.0.0', 'Ipv4Gateway': '0.0.0.0', 'Ipv4PrimaryDNS': '0.0.0.0',
   'Ipv4SecondaryDNS': '0.0.0.0', 'Ipv4SubnetMask': '0.0.0.0', 'Ipv6Address': '::',
   'Ipv6ConfigPolicy': 'Automatic', 'Ipv6Duid': 'Auto', 'Ipv6Gateway': '::',
   'Ipv6PrimaryDNS': '::', 'Ipv6SecondaryDNS': '::', 'LLCDeadLineAllocation':
   'Enabled', 'LlcPrefetch': 'Disabled', 'LocalRemoteThreshold': 'Auto',
   'MaxMemBusFreqMHz': 'Auto', 'MaxPcieSpeed': 'PerPortCtrl', 'MemClearWarmReset':
   'Disabled', 'MemFastTraining': 'Enabled', 'MemMirrorMode': 'Full',
   'MemPatrolScrubbing': 'Enabled', 'MemRefreshRate': 'Refreshx1',
   'MemoryControllerInterleaving': 'Auto', 'MemoryRemap': 'NoAction',
   'MinProcIdlePkgState': 'C6Retention', 'MinProcIdlePower': 'C6',
   'MixedPowerSupplyReporting': 'Enabled', 'NetworkBootRetry': 'Enabled',
   'NetworkBootRetryCount': 20, 'NicBoot1': 'NetworkBoot', 'NicBoot2': 'Disabled',
   'NicBoot3': 'Disabled', 'NicBoot4': 'Disabled', 'NodeInterleaving': 'Disabled',
   'NumaGroupSizeOpt': 'Flat', 'NvmeOptionRom': 'Enabled',
   'OpportunisticSelfRefresh': 'Disabled', 'PciPeerToPeerSerialization':
   'Disabled', 'PciResourcePadding': 'Normal', 'PersistentMemBackupPowerPolicy':
   'WaitForBackupPower', 'PostBootProgress': 'Disabled', 'PostDiscoveryMode':
   'Auto', 'PostF1Prompt': 'Delayed20Sec', 'PostVideoSupport': 'DisplayAll',
   'PowerButton': 'Enabled', 'PowerOnDelay': 'NoDelay', 'PowerRegulator':
   'DynamicPowerSavings', 'PreBootNetwork': 'Auto', 'PrebootNetworkEnvPolicy':
   'Auto', 'PrebootNetworkProxy': '', 'ProcAes': 'Enabled', 'ProcHyperthreading':
   'Enabled', 'ProcTurbo': 'Enabled', 'ProcVirtualization': 'Enabled',
   'ProcX2Apic': 'Enabled', 'ProcessorConfigTDPLevel': 'Normal',
   'ProcessorJitterControl': 'Disabled', 'ProcessorJitterControlFrequency': 0,
   'ProcessorJitterControlOptimization': 'ZeroLatency', 'ProductId': '868703-B21',
   'RedundantPowerSupply': 'BalancedMode', 'RemovableFlashBootSeq':
   'ExternalKeysFirst', 'RestoreDefaults': 'No', 'RestoreManufacturingDefaults':
   'No', 'RomSelection': 'CurrentRom', 'SataSecureErase': 'Disabled',
   'SaveUserDefaults': 'No', 'SecStartBackupImage': 'Disabled', 'SecureBootStatus':
   'Disabled', 'SerialConsoleBaudRate': 'BaudRate115200', 'SerialConsoleEmulation':
   'Vt100Plus', 'SerialConsolePort': 'Auto', 'SerialNumber': 'SGH744YPVS',
   'ServerAssetTag': '', 'ServerConfigLockStatus': 'Disabled', 'ServerName':
   'localhost', 'ServerOtherInfo': '', 'ServerPrimaryOs': '', 'ServiceEmail': '',
   'ServiceName': '', 'ServiceOtherInfo': '', 'ServicePhone': '',
   'SetupBrowserSelection': 'Auto', 'Sriov': 'Enabled', 'StaleAtoS': 'Disabled',
   'SubNumaClustering': 'Disabled', 'ThermalConfig': 'OptimalCooling',
   'ThermalShutdown': 'Enabled', 'TimeFormat': 'Utc', 'TimeZone': 'Utc0',
   'TpmChipId': 'None', 'TpmFips': 'NotSpecified', 'TpmState': 'NotPresent',
   'TpmType': 'NoTpm', 'UefiOptimizedBoot': 'Disabled', 'UefiSerialDebugLevel':
   'Disabled', 'UefiShellBootOrder': 'Disabled', 'UefiShellScriptVerification':
   'Disabled', 'UefiShellStartup': 'Disabled', 'UefiShellStartupLocation': 'Auto',
   'UefiShellStartupUrl': '', 'UefiShellStartupUrlFromDhcp': 'Disabled',
   'UncoreFreqScaling': 'Auto', 'UrlBootFile': '', 'UrlBootFile2': '',
   'UrlBootFile3': '', 'UrlBootFile4': '', 'UsbBoot': 'Enabled', 'UsbControl':
   'UsbEnabled', 'UserDefaultsState': 'Disabled', 'UtilityLang': 'English',
   'VirtualInstallDisk': 'Disabled', 'VirtualSerialPort': 'Com1Irq4',
   'VlanControl': 'Disabled', 'VlanId': 0, 'VlanPriority': 0, 'WakeOnLan':
   'Enabled', 'WorkloadProfile': 'GeneralPowerEfficientCompute', 'XptPrefetcher':
   'Auto', 'iSCSIPolicy': 'SoftwareInitiator'}
```

set_bios_settings(data=None, only_allowed_settings=False)
---------------------------------------------------------

Sets current BIOS settings to the provided data. Takes a dictionary of BIOS settings to be appplied as argument.

When *only_allowed_settings* is set to True, only allowed BIOS settings are returned

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> data = {
   "BootOrderPolicy": "AttemptOnce",
   "IntelPerfMonitoring": "Enabled",
   "IntelProcVtd": "Disabled",
   "UefiOptimizedBoot": "Disabled",
   "PowerProfile": "MaxPerf"}

   >>> apply_filter = True

   >>> ilo_client.set_bios_settings(data = data, only_allowed_settings= apply_filter)
```

When *only_allowed_settings* is set to False, all the BIOS settings supported by iLO are returned

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> apply_filter = False

   >>> ilo_client.set_bios_settings(data, apply_filter)
```

get_default_bios_settings(only_allowed_settings=False)
------------------------------------------------------

Returns default BIOS settings.

When *only_allowed_settings* is set to True, only allowed BIOS settings are returned

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_default_bios_settings(True)

   {'PowerRegulator': u'DynamicPowerSavings', 'AdvancedMemProtection':
   u'AdvancedEcc', 'DynamicPowerCapping': u'Disabled', 'BootOrderPolicy':
   u'RetryIndefinitely', 'Sriov': u'Enabled', 'AutoPowerOn':
   u'RestoreLastState', 'IntelProcVtd': u'Enabled', 'ProcVirtualization':
   u'Enabled', 'ThermalShutdown': u'Enabled', 'IntelTxt': u'Disabled',
   'SecureBootStatus': u'Disabled', 'WorkloadProfile':
   u'GeneralPowerEfficientCompute', 'IntelPerfMonitoring': u'Disabled',
   'TpmType': u'NoTpm', 'UefiOptimizedBoot': u'Enabled', 'ThermalConfig':
   u'OptimalCooling', 'ProcAes': u'Enabled', 'BootMode': u'Uefi',
   'ProcTurbo': u'Enabled', 'IntelligentProvisioning': u'Enabled',
   'ProcHyperthreading': u'Enabled', 'TpmState': u'NotPresent',
   'CollabPowerControl': u'Enabled'}
```

When *only_allowed_settings* is set to False, all the BIOS settings supported by iLO are returned

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_default_bios_settings(False)

   {'AcpiHpet': 'Enabled', 'AcpiRootBridgePxm': 'Enabled', 'AcpiSlit': 'Enabled',
   'AdjSecPrefetch': 'Enabled', 'AdminEmail': '', 'AdminName': '',
   'AdminOtherInfo': '', 'AdminPhone': '', 'AdvCrashDumpMode': 'Disabled',
   'AdvancedMemProtection': 'AdvancedEcc', 'AsrStatus': 'Enabled',
   'AsrTimeoutMinutes': 'Timeout10', 'AssetTagProtection': 'Unlocked',
   'AutoPowerOn': 'RestoreLastState', 'BootMode': 'Uefi', 'BootOrderPolicy':
   'RetryIndefinitely', 'ChannelInterleaving': 'Enabled', 'CollabPowerControl':
   'Enabled', 'ConsistentDevNaming': 'LomsAndSlots', 'CustomPostMessage': '',
   'DaylightSavingsTime': 'Disabled', 'DcuIpPrefetcher': 'Enabled',
   'DcuStreamPrefetcher': 'Enabled', 'Dhcpv4': 'Enabled', 'DynamicPowerCapping':
   'Disabled', 'EmbNicEnable': 'Auto', 'EmbNicLinkSpeed': 'Auto',
   'EmbNicPCIeOptionROM': 'Enabled', 'EmbSas1Aspm': 'Disabled', 'EmbSas1Boot':
   'TwentyFourTargets', 'EmbSas1Enable': 'Auto', 'EmbSas1LinkSpeed': 'Auto',
   'EmbSas1PcieOptionROM': 'Enabled', 'EmbSata1Aspm': 'Disabled', 'EmbSata2Aspm':
   'Disabled', 'EmbVideoConnection': 'Auto', 'EmbeddedDiagnostics': 'Enabled',
   'EmbeddedSata': 'Ahci', 'EmbeddedSerialPort': 'Com2Irq3', 'EmbeddedUefiShell':
   'Enabled', 'EmsConsole': 'Disabled', 'EnabledCoresPerProc': 0,
   'EnergyEfficientTurbo': 'Enabled', 'EnergyPerfBias': 'BalancedPerf',
   'EraseUserDefaults': 'No', 'ExtendedAmbientTemp': 'Disabled', 'ExtendedMemTest':
   'Disabled', 'F11BootMenu': 'Enabled', 'FCScanPolicy': 'CardConfig',
   'FanFailPolicy': 'Shutdown', 'FanInstallReq': 'EnableMessaging', 'FlexLom1Aspm':
   'Disabled', 'HttpSupport': 'Auto', 'HwPrefetcher': 'Enabled',
   'IODCConfiguration': 'Auto', 'IntelDmiLinkFreq': 'Auto', 'IntelNicDmaChannels':
   'Enabled', 'IntelPerfMonitoring': 'Disabled', 'IntelProcVtd': 'Enabled',
   'IntelligentProvisioning': 'Enabled', 'InternalSDCardSlot': 'Enabled',
   'Ipv4Address': '0.0.0.0', 'Ipv4Gateway': '0.0.0.0', 'Ipv4PrimaryDNS': '0.0.0.0',
   'Ipv4SecondaryDNS': '0.0.0.0', 'Ipv4SubnetMask': '0.0.0.0', 'Ipv6Address': '::',
   'Ipv6ConfigPolicy': 'Automatic', 'Ipv6Duid': 'Auto', 'Ipv6Gateway': '::',
   'Ipv6PrimaryDNS': '::', 'Ipv6SecondaryDNS': '::', 'LLCDeadLineAllocation':
   'Enabled', 'LlcPrefetch': 'Disabled', 'LocalRemoteThreshold': 'Auto',
   'MaxMemBusFreqMHz': 'Auto', 'MaxPcieSpeed': 'PerPortCtrl', 'MemClearWarmReset':
   'Disabled', 'MemFastTraining': 'Enabled', 'MemMirrorMode': 'Full',
   'MemPatrolScrubbing': 'Enabled', 'MemRefreshRate': 'Refreshx1',
   'MemoryControllerInterleaving': 'Auto', 'MemoryRemap': 'NoAction',
   'MinProcIdlePkgState': 'C6Retention', 'MinProcIdlePower': 'C6',
   'MixedPowerSupplyReporting': 'Enabled', 'NetworkBootRetry': 'Enabled',
   'NetworkBootRetryCount': 20, 'NicBoot1': 'NetworkBoot', 'NicBoot2': 'Disabled',
   'NicBoot3': 'Disabled', 'NicBoot4': 'Disabled', 'NodeInterleaving': 'Disabled',
   'NumaGroupSizeOpt': 'Flat', 'NvmeOptionRom': 'Enabled',
   'OpportunisticSelfRefresh': 'Disabled', 'PciPeerToPeerSerialization':
   'Disabled', 'PciResourcePadding': 'Normal', 'PersistentMemBackupPowerPolicy':
   'WaitForBackupPower', 'PostBootProgress': 'Disabled', 'PostDiscoveryMode':
   'Auto', 'PostF1Prompt': 'Delayed20Sec', 'PostVideoSupport': 'DisplayAll',
   'PowerButton': 'Enabled', 'PowerOnDelay': 'NoDelay', 'PowerRegulator':
   'DynamicPowerSavings', 'PreBootNetwork': 'Auto', 'PrebootNetworkEnvPolicy':
   'Auto', 'PrebootNetworkProxy': '', 'ProcAes': 'Enabled', 'ProcHyperthreading':
   'Enabled', 'ProcTurbo': 'Enabled', 'ProcVirtualization': 'Enabled',
   'ProcX2Apic': 'Enabled', 'ProcessorConfigTDPLevel': 'Normal',
   'ProcessorJitterControl': 'Disabled', 'ProcessorJitterControlFrequency': 0,
   'ProcessorJitterControlOptimization': 'ZeroLatency', 'RedundantPowerSupply':
   'BalancedMode', 'RemovableFlashBootSeq': 'ExternalKeysFirst', 'RestoreDefaults':
   'No', 'RestoreManufacturingDefaults': 'No', 'SataSecureErase': 'Disabled',
   'SaveUserDefaults': 'No', 'SecStartBackupImage': 'Disabled', 'SecureBootStatus':
   'Disabled', 'SerialConsoleBaudRate': 'BaudRate115200', 'SerialConsoleEmulation':
   'Vt100Plus', 'SerialConsolePort': 'Auto', 'ServerAssetTag': '',
   'ServerConfigLockStatus': 'Disabled', 'ServerName': '', 'ServerOtherInfo': '',
   'ServerPrimaryOs': '', 'ServiceEmail': '', 'ServiceName': '',
   'ServiceOtherInfo': '', 'ServicePhone': '', 'SetupBrowserSelection': 'Auto',
   'Sriov': 'Enabled', 'StaleAtoS': 'Disabled', 'SubNumaClustering': 'Disabled',
   'ThermalConfig': 'OptimalCooling', 'ThermalShutdown': 'Enabled', 'TimeFormat':
   'Utc', 'TimeZone': 'Utc0', 'TpmChipId': 'None', 'TpmFips': 'NotSpecified',
   'TpmState': 'NotPresent', 'TpmType': 'NoTpm', 'UefiOptimizedBoot': 'Enabled',
   'UefiSerialDebugLevel': 'Disabled', 'UefiShellBootOrder': 'Disabled',
   'UefiShellScriptVerification': 'Disabled', 'UefiShellStartup': 'Disabled',
   'UefiShellStartupLocation': 'Auto', 'UefiShellStartupUrl': '',
   'UefiShellStartupUrlFromDhcp': 'Disabled', 'UncoreFreqScaling': 'Auto',
   'UrlBootFile': '', 'UrlBootFile2': '', 'UrlBootFile3': '', 'UrlBootFile4': '',
   'UsbBoot': 'Enabled', 'UsbControl': 'UsbEnabled', 'UserDefaultsState':
   'Disabled', 'UtilityLang': 'English', 'VirtualInstallDisk': 'Disabled',
   'VirtualSerialPort': 'Com1Irq4', 'VlanControl': 'Disabled', 'VlanId': 0,
   'VlanPriority': 0, 'WakeOnLan': 'Enabled', 'WorkloadProfile':
   'GeneralPowerEfficientCompute', 'XptPrefetcher': 'Auto', 'iSCSIPolicy':
   'SoftwareInitiator'}
```

delete_raid_configuration()
---------------------------

Deletes all logical drives from the system.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.delete_raid_configuration()
```

create_raid_configuration(raid_config)
--------------------------------------

Creates raid configuration on the hardware. Takes a dictionary containing target raid configuration data as argument.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> raid_config = {
   'logical_disks': [{'size_gb': 279,
                      'physical_disks': [u'1I:1:2'],
                      'raid_level': u'0'}]}

   >>> ilo_client.create_raid_configuration(raid_config)
```

read_raid_configuration(raid_config=None)
-----------------------------------------

Reads the raid configuration of the hardware. In case of post-delete read the *raid_config* value is None. In case of post-create, *raid_config* is a dictionary containing target raid configuration data.

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.read_raid_configuration()

   {'logical_disks': [{'size_gb': 279, 'physical_disks': [u'1I:1:2'],
   'raid_level': u'0', 'root_device_hint': {'wwn':
   u'0x600508B1001C99DF1EAFA712BAFECD59'}, 'controller': None,
   'volume_name': u'd625fcce-6750-4b5a-93e1-a08abf7f6060'}]}
```

get_bios_settings_result()
--------------------------

Returns the result of bios settings applied

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.get_bios_settings_result()

   {'status': 'success', 'results': [{u'MessageId': u'Base.1.0.Success'}]}
```

add_tls_certificate(cert_file_list)
-----------------------------------

Adds the TLS certificate to the iLO

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> ilo_client.add_tls_certificate(['/xyz/ilo.crt'])
```

remove_tls_certificate(fp_list)
-----------------------------------

Removes the TLS certificate from the iLO

```
   >>> from proliantutils.ilo import client

   >>> ilo_client = client.IloClient('10.10.1.57', 'Administrator', 'password')

   >>> fp = 'FA:3A:68:C7:7E:ED:90:21:D2:FA:3E:54:6B:0C:14:D3:2F:8D:43:50:F7:05:A7:0F:1C:68:35:DB:5C:D2:53:28'

   >>> ilo_client.remove_tls_certificate([fp])
```
