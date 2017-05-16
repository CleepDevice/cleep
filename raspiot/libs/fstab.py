from console import Console
from raspiot.utils import MissingParameter

class Fstab():
    """
    Handles /etc/fstab file
    """

    MODE_RO = 'r'
    MODE_RW = 'w'

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
        self.__fd = open('/etc/fstab', mode)
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
        res = self.console.command('blkid | grep "%s"' % device)
        if res['error'] or res['killed']:
            return None
        else:
            items = res['stdout'][0].split()
            for item in items:
                if item.lower().startswith('uuid='):
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
        res = self.console.command('blkid | grep "%s"' % uuid)
        if res['error'] or res['killed']:
            return None
        else:
            items = res['stdout'].split()
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

        res = self.console.command('blkid')
        if res['error'] or res['killed']:
            return None

        else:
            for line in res['stdout']:
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
        
        Args:
            mountpoint (string): mountpoint to delete
        
        Returns:
            bool: True if removed, False otherwise

        Raises:
            MissingParameter
        """
        if options is None or len(options)==0:
            raise MissingParameter('Mountpoint parameter is missing')
        return False

    def reload_fstab(self):
        """
        Reload fstab file (mount -a)
        
        Returns:
            bool: True if command successful, False otherwise
        """
        res = self.console.command('/bin/mount -a')
        if res['error'] or res['killed']:
            return False
        else:
            return True


