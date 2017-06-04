from console import Console
from raspiot.utils import MissingParameter

class Fstab():
    """
    Handles /etc/fstab file
    """

    MODE_RO = u'r'
    MODE_RW = u'w'

    def __init__(self):
        """
        Constructor
        """
        self.__fd = None
        self.console = Console()

    def __del__(self):
        """
        Destructor
        """
        if self.__fd is not None:
            self.__fd.close()

    def __open_file(self, mode):
        """
        Open file on specified mode

        Args:
            mode (r|w): opening mode

        Returns:
            file: file descriptor
        """
        #close existing file descriptor first
        if self.__fd is not None:
            self.__fd.close()
            
        #open and return file descriptor
        self.__fd = open(u'/etc/fstab', mode)
        return self.__fd

    def get_uuid_by_device(self, device):
        """
        Return uuid corresponding to device

        Args:
            device (string): device as presented in fstab

        Returns:
            string: uuid
            None: if nothing found
        """
        res = self.console.command(u'/sbin/blkid | grep "%s"' % device)
        if res[u'error'] or res[u'killed']:
            return None
        else:
            items = res[u'stdout'][0].split()
            for item in items:
                if item.lower().startswith(u'uuid='):
                    return item[5:].replace('"', '').strip()

        return None

    def get_device_by_uuid(self, uuid):
        """
        Return device corresponding to uuid

        Args:
            uuid (string): device uuid

        Returns:
            string: device
            None: if nothing found
        """
        res = self.console.command(u'/sbin/blkid | grep "%s"' % uuid)
        if res[u'error'] or res['ukilled']:
            return None
        else:
            items = res[u'stdout'].split()
            return items[0].replace(':', '').strip()

        return None

    def get_all_devices(self):
        """
        Return all devices as returned by command blkid

        Returns:
            dict: list of devices
                {
                    'device': {
                        device: '',
                        uuid: ''
                    },
                    ...
                }
        """
        devices = {}

        res = self.console.command(u'/sbin/blkid')
        if res[u'error'] or res[u'killed']:
            return None

        else:
            for line in res[u'stdout']:
                device = {
                    u'device': None,
                    u'uuid': None
                }
                items = line.split()
                device[u'device'] = items[0].replace(u':', u'').strip()
                for item in items:
                    if item.lower().startswith(u'uuid='):
                        device[u'uuid'] = item[5:].replace(u'"', u'').strip()
                        break
                devices[device[u'device']] = device

        return devices

    def get_mountpoints(self):
        """
        Return all mountpoints as presented in /etc/fstab file

        Returns:
            dict: list of mountpoints
                {
                    'mountpoint': {
                        device: '',
                        uuid: '',
                        mountpoint: '',
                        mounttype: '',
                        options: ''
                    },
                    ...
                }
        """
        mountpoints = {}

        fd = self.__open_file(self.MODE_RO)
        for line in fd.readlines():
            line = line.strip()

            if line.startswith(u'#'):
                #drop comment line
                continue

            elif line.startswith(u'/dev/'):
                #device specified
                (device, mountpoint, mounttype, options, _, _) = line.split()
                uuid = self.get_uuid_by_device(device)
                mountpoints[mountpoint] = {
                    u'device': device,
                    u'uuid': uuid,
                    u'mountpoint': mountpoint,
                    u'mounttype': mounttype,
                    u'options': options
                }

            elif line.strip().lower()[:4]==u'uuid':
                #uuid specified
                (uuid, mountpoint, mounttype, options, _, _) = line.split()
                uuid = uuid.split(u'=')[1].strip()
                device = self.get_device_by_uuid(uuid)
                mountpoints[mountpoint] = {
                    u'device': device,
                    u'uuid': uuid.split(u'=')[1].strip(),
                    u'mountpoint': mountpoint,
                    u'mounttype': mounttype,
                    u'options': options
                }

        return mountpoints

    def add_mountpoint(self, mountpoint, device, mounttype, options):
        """
        Add specified mount point to /etc/fstab file

        Args:
            mountpoint (string): mountpoint
            device (string): device path
            mounttype (string): type of mountpoint (ext4, ext3...)
            options (string): specific options for mountpoint
                              
        Returns:
            bool: True if mountpoint added succesfully, False otherwise

        Raises:
            MissingParameter
        """
        if mountpoint is None or len(mountpoint)==0:
            raise MissingParameter(u'Mountpoint parameter is missing')
        if device is None or len(device)==0:
            raise MissingParameter(u'Device parameter is missing')
        if mounttype is None or len(mounttype)==0:
            raise MissingParameter(u'Mounttype parameter is missing')
        if options is None or len(options)==0:
            raise MissingParameter(u'Options parameter is missing')
        return False

    def delete_mountpoint(self, mountpoint):
        """
        Delete specified mount point from /etc/fstab file
        
        Args:
            mountpoint (string): mountpoint to delete
        
        Returns:
            bool: True if removed, False otherwise

        Raises:
            MissingParameter
        """
        if options is None or len(options)==0:
            raise MissingParameter(u'Mountpoint parameter is missing')
        return False

    def reload_fstab(self):
        """
        Reload fstab file (mount -a)
        
        Returns:
            bool: True if command successful, False otherwise
        """
        res = self.console.command(u'/bin/mount -a')
        if res[u'error'] or res[u'killed']:
            return False
        else:
            return True


