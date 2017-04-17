from console import Console
from raspiot.utils import MissingParameter

class Fstab():
    """
    Handles /etc/fstab file
    """

    MODE_RO = 'r'
    MODE_RW = 'w'

    def __init__(self):
        self.__fd = None
        self.console = Console()

    def __del__(self):
        if self.__fd is not None:
            self.__fd.close()

    def __open_file(self, mode):
        """
        Open file on specified mode
        @param mode: opening mode (MODE_RO|MODE_RW)
        @return file descriptor
        """
        #close existing file descriptor first
        if self.__fd is not None:
            self.__fd.close()
            
        #open and return file descriptor
        self.__fd = open('/etc/fstab', mode)
        return self.__fd

    def get_uuid_by_device(self, device):
        """
        Return uuid corresponding to device
        @param device: device as presented in fstab
        @return uuid (string) or None if nothing found
        """
        res = self.console.command('blkid | grep "%s"' % device)
        if res['error'] or res['killed']:
            return None
        else:
            items = res['output'][0].split()
            for item in items:
                if item.lower().startswith('uuid='):
                    return item[5:].replace('"', '').strip()

        return None

    def get_device_by_uuid(self, uuid):
        """
        Return device corresponding to uuid
        @param uuid: device uuid (string)
        @return device (string) or None if nothing found
        """
        res = self.console.command('blkid | grep "%s"' % uuid)
        if res['error'] or res['killed']:
            return None
        else:
            items = res['output'].split()
            return items[0].replace(':', '').strip()

        return None

    def get_all_devices(self):
        """
        Return all devices as returned by command blkid
        @return list of devices (dict('device':dict(device, uuid), ...))
        """
        devices = {}

        res = self.console.command('blkid')
        if res['error'] or res['killed']:
            return None

        else:
            for line in res['output']:
                device = {
                    'device': None,
                    'uuid': None
                }
                items = line.split()
                device['device'] = items[0].replace(':', '').strip()
                for item in items:
                    if item.lower().startswith('uuid='):
                        device['uuid'] = item[5:].replace('"', '').strip()
                        break
                devices[device['device']] = device

        return devices

    def get_mountpoints(self):
        """
        Return all mountpoints as presented in /etc/fstab file
        @return list of mountpoints (dict('mountpoint': dict(device, uuid, mountpoint, mounttype, options'), ...))
        """
        mountpoints = {}

        fd = self.__open_file(self.MODE_RO)
        for line in fd.readlines():
            line = line.strip()

            if line.startswith('#'):
                #drop comment line
                continue

            elif line.startswith('/dev/'):
                #device specified
                (device, mountpoint, mounttype, options, _, _) = line.split()
                uuid = self.get_uuid_by_device(device)
                mountpoints[mountpoint] = {
                    'device': device,
                    'uuid': uuid,
                    'mountpoint': mountpoint,
                    'mounttype': mounttype,
                    'options': options
                }

            elif line.strip().lower()[:4]=='uuid':
                #uuid specified
                (uuid, mountpoint, mounttype, options, _, _) = line.split()
                uuid = uuid.split('=')[1].strip()
                device = self.get_device_by_uuid(uuid)
                mountpoints[mountpoint] = {
                    'device': device,
                    'uuid': uuid.split('=')[1].strip(),
                    'mountpoint': mountpoint,
                    'mounttype': mounttype,
                    'options': options
                }

        return mountpoints

    def add_mountpoint(self, mountpoint, device, mounttype, options):
        """
        Add specified mount point to /etc/fstab file
        @param mountpoint: mountpoint (string)
        @param device: device path (string)
        @param mounttype: type of mountpoint (ext4, ext3...)
        @param options: specific options for mountpoint
        @return True if mountpoint added succesfully, False otherwise
        @raise MissingParameter
        """
        if mountpoint is None or len(mountpoint)==0:
            raise MissingParameter('Mountpoint parameter is missing')
        if device is None or len(device)==0:
            raise MissingParameter('Device parameter is missing')
        if mounttype is None or len(mounttype)==0:
            raise MissingParameter('Mounttype parameter is missing')
        if options is None or len(options)==0:
            raise MissingParameter('Options parameter is missing')
        return False

    def delete_mountpoint(self, mountpoint):
        """
        Delete specified mount point from /etc/fstab file
        @param mountpoint: mountpoint to delete (string)
        @return True if removed, False otherwise
        @raise MissingParameter
        """
        if options is None or len(options)==0:
            raise MissingParameter('Mountpoint parameter is missing')
        return False

    def reload_fstab(self):
        """
        Reload fstab file (mount -a)
        @return True if command successful, False otherwise
        """
        res = self.console.command('/bin/mount -a')
        if res['error'] or res['killed']:
            return False
        else:
            return True


