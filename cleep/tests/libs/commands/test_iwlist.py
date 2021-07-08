#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)).replace('tests/', ''))
from iwlist import Iwlist
from cleep.libs.configs.wpasupplicantconf import WpaSupplicantConf
from cleep.libs.tests.lib import TestLib
from unittest.mock import Mock
import unittest
import logging
from pprint import pformat

SAMPLE = """wlan0     Scan completed :
          Cell 01 - Address: 00:11:95:07:EC:7A
                    Channel:6
                    Frequency:2.437 GHz (Channel 6)
                    Quality=70/70  Signal level=39/100 Noise level=0/100
                    Encryption key:on
                    ESSID:"Network Wifi2"
                    Bit Rates:1 Mb/s; 2 Mb/s; 5.5 Mb/s; 11 Mb/s; 6 Mb/s
                              12 Mb/s; 24 Mb/s; 36 Mb/s
                    Bit Rates:9 Mb/s; 18 Mb/s; 48 Mb/s; 54 Mb/s
                    Mode:Master
                    Extra:tsf=0000000000000000
                    Extra: Last beacon: 60ms ago
                    IE: Unknown: 000D426F6E6E656175205769666932
                    IE: Unknown: 010882848B960C183048
                    IE: Unknown: 030106
                    IE: Unknown: 2A0100
                    IE: Unknown: 32041224606C
                    IE: IEEE 802.11i/WPA2 Version 1
                        Group Cipher : CCMP  
                        Pairwise Ciphers (1) : CCMP
                        Authentication Suites (1) : PSK
                       Preauthentication Supported
                    IE: Unknown: DD0900037F0101000EFF7F
                    IE: Unknown: DD0C00037F020101000002A34000
                    IE: Unknown: DD1A00037F030100000000119507EC7A02119507EC7A64002C010E08
          Cell 02 - Address: B6:39:56:76:D7:9C
                    Channel:9
                    Frequency:2.452 GHz (Channel 9)
                    Quality=42/70  Signal level=-68 dBm
                    Encryption key:on
                    ESSID:"MyWifiNetwork"
                    Bit Rates:1 Mb/s; 2 Mb/s; 5.5 Mb/s; 11 Mb/s; 6 Mb/s
                              9 Mb/s; 12 Mb/s; 18 Mb/s
                    Bit Rates:24 Mb/s; 36 Mb/s; 48 Mb/s; 54 Mb/s
                    Mode:Master
                    Extra:tsf=0000000000000000
                    Extra: Last beacon: 60ms ago
                    IE: Unknown: 000854616E6757696669
                    IE: Unknown: 010882848B960C121824
                    IE: Unknown: 030109
                    IE: Unknown: 0706444520010D7F
                    IE: Unknown: 2A0100
                    IE: Unknown: 32043048606C
                    IE: Unknown: 460573D000000C
                    IE: Unknown: 2D1AEF1903FFFF000000000000000000000100000000000000000000
                    IE: Unknown: 3D1609050000000000000000000000000000000000000000
                    IE: Unknown: 4A0E14000A002C01C800140005001900
                    IE: Unknown: 7F0805000F0200000040
                    IE: Unknown: BF0CB2418033FAFF0000FAFF0000
                    IE: Unknown: C005000000FCFF
                    IE: Unknown: DD180050F2020101800003A4000027A4000042435E0062322F00
                    IE: Unknown: DD0900037F01010000FF7F
                    IE: IEEE 802.11i/WPA2 Version 1
                        Group Cipher : CCMP  
                        Pairwise Ciphers (1) : CCMP
                        Authentication Suites (1) : PSK
                    IE: Unknown: DD7F0050F204104A0001101044000102103B00010310470010876543219ABCDEF01234B0395676D79C1021000B6F70656E7772742E6F726710230003574150102400033132331042000531323334351054000800060050F204000110110012524253343028576972656C657373204150291008000200001049000600372A000120
          Cell 03 - Address: B6:39:56:76:D5:58
                    Channel:13
                    Frequency:2.472 GHz (Channel 13)
                    Quality=42/70  Signal level=-68 dBm
                    Encryption key:on
                    ESSID:"MyWifiNetwork"
                    Bit Rates:1 Mb/s; 2 Mb/s; 5.5 Mb/s; 11 Mb/s; 6 Mb/s
                              9 Mb/s; 12 Mb/s; 18 Mb/s
                    Bit Rates:24 Mb/s; 36 Mb/s; 48 Mb/s; 54 Mb/s
                    Mode:Master
                    Extra:tsf=0000000000000000
                    Extra: Last beacon: 60ms ago
                    IE: Unknown: 000854616E6757696669
                    IE: Unknown: 010882848B960C121824
                    IE: Unknown: 03010D
                    IE: Unknown: 072A4445200101140201140301140401140501140601140701140801140901140A01140B01140C01140D0114
                    IE: Unknown: 2A0100
                    IE: Unknown: 32043048606C
                    IE: Unknown: 460573D000000C
                    IE: Unknown: 2D1AAD0903FFFF000000000000000000000100000000000000000000
                    IE: Unknown: 3D160D000400000000000000000000000000000000000000
                    IE: Unknown: 4A0E14000A002C01C800140005001900
                    IE: Unknown: 7F0805000F0200000040
                    IE: Unknown: BF0CB2418033FAFF0000FAFF0000
                    IE: Unknown: C005000000FCFF
                    IE: Unknown: DD180050F2020101800003A4000027A4000042435E0062322F00
                    IE: Unknown: DD0900037F01010000FF7F
                    IE: IEEE 802.11i/WPA2 Version 1
                        Group Cipher : CCMP  
                        Pairwise Ciphers (1) : CCMP
                        Authentication Suites (1) : PSK
                    IE: Unknown: DD7F0050F204104A0001101044000102103B00010310470010876543219ABCDEF01234B0395676D5581021000B6F70656E7772742E6F726710230003574150102400033132331042000531323334351054000800060050F204000110110012524252343028576972656C657373204150291008000200001049000600372A000120
                    IE: Unknown: DD0B00146C0007040000000000
          Cell 04 - Address: B0:39:56:76:D7:9F
                    Channel:36
                    Frequency:5.18 GHz (Channel 36)
                    Quality=38/70  Signal level=-72 dBm
                    Encryption key:on
                    ESSID:"MyWifiNetwork"
                    Bit Rates:6 Mb/s; 9 Mb/s; 12 Mb/s; 18 Mb/s; 24 Mb/s
                              36 Mb/s; 48 Mb/s; 54 Mb/s
                    Mode:Master
                    Extra:tsf=0000000000000000
                    Extra: Last beacon: 60ms ago
                    IE: Unknown: 000854616E6757696669
                    IE: Unknown: 01088C129824B048606C
                    IE: Unknown: 030124
                    IE: Unknown: 071C44452024017F28017F2C017F30017F34017F38017F3C017F40017F00
                    IE: Unknown: 460573D000000C
                    IE: Unknown: 2D1AEF0903FFFF000000000000000000000100000000000000000000
                    IE: Unknown: 3D1624050000000000000000000000000000000000000000
                    IE: Unknown: 7F0804000F0200000040
                    IE: Unknown: BF0CF2618033FAFF0000FAFF0000
                    IE: Unknown: C005012A00FCFF
                    IE: Unknown: C305037F7F7F7F
                    IE: Unknown: DD180050F2020101800003A4000027A4000042435E0062322F00
                    IE: Unknown: DD0900037F01010000FF7F
                    IE: IEEE 802.11i/WPA2 Version 1
                        Group Cipher : CCMP  
                        Pairwise Ciphers (1) : CCMP
                        Authentication Suites (1) : PSK
                    IE: Unknown: DD840050F204104A0001101044000102103B00010310470010876543219ABCDEF01234B0395676D79C1021000B6F70656E7772742E6F726710230003574150102400033132331042000531323334351054000800060050F204000110110012524253343028576972656C65737320415029100800020000103C0001021049000600372A000120
          Cell 05 - Address: B0:39:56:76:D5:5B
                    Channel:36
                    Frequency:5.18 GHz (Channel 36)
                    Quality=31/70  Signal level=-79 dBm
                    Encryption key:on
                    ESSID:"MyWifiNetwork"
                    Bit Rates:6 Mb/s; 9 Mb/s; 12 Mb/s; 18 Mb/s; 24 Mb/s
                              36 Mb/s; 48 Mb/s; 54 Mb/s
                    Mode:Master
                    Extra:tsf=0000000000000000
                    Extra: Last beacon: 60ms ago
                    IE: Unknown: 000854616E6757696669
                    IE: Unknown: 01088C129824B048606C
                    IE: Unknown: 030124
                    IE: Unknown: 071C4445202401172801172C01173001173401173801173C011740011700
                    IE: Unknown: 460573D000000C
                    IE: Unknown: 2D1AEF0903FFFF000000000000000000000100000000000000000000
                    IE: Unknown: 3D1624050600000000000000000000000000000000000000
                    IE: Unknown: 7F0804000F0200000040
                    IE: Unknown: BF0CF2618033FAFF0000FAFF0000
                    IE: Unknown: C005012A00FCFF
                    IE: Unknown: C305037F7F7F7F
                    IE: Unknown: DD180050F2020101800003A4000027A4000042435E0062322F00
                    IE: Unknown: DD0900037F01010000FF7F
                    IE: IEEE 802.11i/WPA2 Version 1
                        Group Cipher : CCMP  
                        Pairwise Ciphers (1) : CCMP
                        Authentication Suites (1) : PSK
                    IE: Unknown: DD840050F204104A0001101044000102103B00010310470010876543219ABCDEF01234B0395676D5581021000B6F70656E7772742E6F726710230003574150102400033132331042000531323334351054000800060050F204000110110012524252343028576972656C65737320415029100800020000103C0001021049000600372A000120
                    IE: Unknown: DD0B00146C0007040000000000
          Cell 06 - Address: B0:39:56:76:D7:9E
                    Channel:108
                    Frequency:5.54 GHz (Channel 108)
                    Quality=37/70  Signal level=-73 dBm
                    Encryption key:on
                    ESSID:""
                    Bit Rates:6 Mb/s; 9 Mb/s; 12 Mb/s; 18 Mb/s; 24 Mb/s
                              36 Mb/s; 48 Mb/s; 54 Mb/s
                    Mode:Master
                    Extra:tsf=0000000000000000
                    Extra: Last beacon: 60ms ago
                    IE: Unknown: 0000
                    IE: Unknown: 01088C129824B048606C
                    IE: Unknown: 03016C
                    IE: Unknown: 050400010000
                    IE: Unknown: 072444452064017F68017F6C017F70017F74017F78017F7C017F80017F84017F88017F8C017F
                    IE: Unknown: 200103
                    IE: Unknown: 2D1AEF0903FFFF000000000000000000000100000000000000000000
                    IE: Unknown: 3D166C050000000000000000000000000000000000000000
                    IE: Unknown: 4A0E14000A002C01C800140005001900
                    IE: Unknown: 7F0805000F0200000040
                    IE: Unknown: BF0CB2598933FAFF0000FAFF0000
                    IE: Unknown: C005016A00FCFF
                    IE: Unknown: C304027F7F7F
                    IE: Unknown: DD180050F2020101800003A4000027A4000042435E0062322F00
                    IE: Unknown: DD0900037F01010000FF7F
                    IE: IEEE 802.11i/WPA2 Version 1
                        Group Cipher : CCMP  
                        Pairwise Ciphers (1) : CCMP
                        Authentication Suites (1) : PSK
                    IE: Unknown: DD0B00146C0407050000000000
                    IE: Unknown: DD1F8CFDF000000101000100000000000000000000B0395676D79EBA395676D79C
          Cell 07 - Address: B0:39:56:76:D5:5A
                    Channel:108
                    Frequency:5.54 GHz (Channel 108)
                    Quality=50/70  Signal level=-60 dBm
                    Encryption key:on
                    ESSID:""
                    Bit Rates:6 Mb/s; 9 Mb/s; 12 Mb/s; 18 Mb/s; 24 Mb/s
                              36 Mb/s; 48 Mb/s; 54 Mb/s
                    Mode:Master
                    Extra:tsf=0000000000000000
                    Extra: Last beacon: 60ms ago
                    IE: Unknown: 0000
                    IE: Unknown: 01088C129824B048606C
                    IE: Unknown: 03016C
                    IE: Unknown: 050400010000
                    IE: Unknown: 072444452064011E68011E6C011E70011E74011E78011E7C011E80011E84011E88011E8C011E
                    IE: Unknown: 200103
                    IE: Unknown: 2D1AEF0903FFFF000000000000000000000100000000000000000000
                    IE: Unknown: 3D166C050000000000000000000000000000000000000000
                    IE: Unknown: 4A0E14000A002C01C800140005001900
                    IE: Unknown: 7F0805000F0200000040
                    IE: Unknown: BF0CB2598933FAFF0000FAFF0000
                    IE: Unknown: C005016A00FCFF
                    IE: Unknown: C304027F7F7F
                    IE: Unknown: DD180050F2020101800003A4000027A4000042435E0062322F00
                    IE: Unknown: DD0900037F01010000FF7F
                    IE: IEEE 802.11i/WPA2 Version 1
                        Group Cipher : CCMP  
                        Pairwise Ciphers (1) : CCMP
                        Authentication Suites (1) : PSK
                    IE: Unknown: DD0B00146C0407040000000000
                    IE: Unknown: DD1F8CFDF00000010100000100000000000000FFFFB0395676D55ABA395676D558
          Cell 08 - Address: BA:39:56:76:D7:9C
                    Channel:9
                    Frequency:2.452 GHz (Channel 9)
                    Quality=41/70  Signal level=-69 dBm
                    Encryption key:on
                    ESSID:""
                    Bit Rates:1 Mb/s; 2 Mb/s; 5.5 Mb/s; 11 Mb/s; 6 Mb/s
                              9 Mb/s; 12 Mb/s; 18 Mb/s
                    Bit Rates:24 Mb/s; 36 Mb/s; 48 Mb/s; 54 Mb/s
                    Mode:Master
                    Extra:tsf=0000000000000000
                    Extra: Last beacon: 60ms ago
                    IE: Unknown: 0000
                    IE: Unknown: 010882848B960C121824
                    IE: Unknown: 030109
                    IE: Unknown: 050400010000
                    IE: Unknown: 0706444520010D7F
                    IE: Unknown: 2A0100
                    IE: Unknown: 32043048606C
                    IE: Unknown: 2D1AEF1903FFFF000000000000000000000100000000000000000000
                    IE: Unknown: 3D1609050000000000000000000000000000000000000000
                    IE: Unknown: 4A0E14000A002C01C800140005001900
                    IE: Unknown: 7F0805000F0200000040
                    IE: Unknown: BF0CB2598933FAFF0000FAFF0000
                    IE: Unknown: C005000000FCFF
                    IE: Unknown: DD180050F2020101800003A4000027A4000042435E0062322F00
                    IE: Unknown: DD0900037F01010000FF7F
                    IE: IEEE 802.11i/WPA2 Version 1
                        Group Cipher : CCMP  
                        Pairwise Ciphers (1) : CCMP
                        Authentication Suites (1) : PSK
                    IE: Unknown: DD0B00146C0407050000000000
                    IE: Unknown: DD1F8CFDF000000101000100000000000000000000B0395676D79EBA395676D79C
          Cell 09 - Address: BA:39:56:76:D5:58
                    Channel:13
                    Frequency:2.472 GHz (Channel 13)
                    Quality=44/70  Signal level=-66 dBm
                    Encryption key:on
                    ESSID:""
                    Bit Rates:1 Mb/s; 2 Mb/s; 5.5 Mb/s; 11 Mb/s; 6 Mb/s
                              9 Mb/s; 12 Mb/s; 18 Mb/s
                    Bit Rates:24 Mb/s; 36 Mb/s; 48 Mb/s; 54 Mb/s
                    Mode:Master
                    Extra:tsf=0000000000000000
                    Extra: Last beacon: 60ms ago
                    IE: Unknown: 0000
                    IE: Unknown: 010882848B960C121824
                    IE: Unknown: 03010D
                    IE: Unknown: 050400010000
                    IE: Unknown: 072A4445200101140201140301140401140501140601140701140801140901140A01140B01140C01140D0114
                    IE: Unknown: 2A0100
                    IE: Unknown: 32043048606C
                    IE: Unknown: 2D1AAD0903FFFF000000000000000000000100000000000000000000
                    IE: Unknown: 3D160D000400000000000000000000000000000000000000
                    IE: Unknown: 4A0E14000A002C01C800140005001900
                    IE: Unknown: 7F0805000F0200000040
                    IE: Unknown: BF0CB2598933FAFF0000FAFF0000
                    IE: Unknown: C005000000FCFF
                    IE: Unknown: DD180050F2020101800003A4000027A4000042435E0062322F00
                    IE: Unknown: DD0900037F01010000FF7F
                    IE: IEEE 802.11i/WPA2 Version 1
                        Group Cipher : CCMP  
                        Pairwise Ciphers (1) : CCMP
                        Authentication Suites (1) : PSK
                    IE: Unknown: DD0B00146C0407040000000000
                    IE: Unknown: DD1F8CFDF00000010100000100000000000000FFFFB0395676D55ABA395676D558
      	  Cell 10 - Address: 88:03:55:E8:3A:D1
                    Channel:1
                    Frequency:2.412 GHz (Channel 1)
		    Quality=29/70  Signal level=-81 dBm  
                    Encryption key:off
                    ESSID:"Unsecured network"
                    Bit Rates:1 Mb/s; 2 Mb/s; 5.5 Mb/s; 11 Mb/s; 9 Mb/s
                              18 Mb/s; 36 Mb/s; 54 Mb/s
                    Bit Rates:6 Mb/s; 12 Mb/s; 24 Mb/s; 48 Mb/s
                    Mode:Master
                    Extra:tsf=000009e127b7513e
                    Extra: Last beacon: 6290ms ago
                    IE: Unknown: 00074B504E20466F6E
                    IE: Unknown: 010882848B961224486C
                    IE: Unknown: 030101
                    IE: Unknown: 2A0104
                    IE: Unknown: 32040C183060
                    IE: Unknown: 2D1A6C0017FFFF0000000000000000000000000000000C0000000000
                    IE: Unknown: 3D1601000400000000000000000000000000000000000000
                    IE: Unknown: 3E0100
                    IE: Unknown: DD180050F2020101000003A4000027A4000042435E0062322F00
                    IE: Unknown: 0B0504001C127A
                    IE: Unknown: 7F0101
                    IE: Unknown: DD8F0050F204104A00011010440001021041000100103B0001031047001000000000000000030000880355E83ADB1021000B436F72706F726174696F6E1023000B564756373531394B5732321024000930322E30302E3133361042000A413334343030333035311054000800060050F204000110110014576972656C65737320526F757465722857464129100800020084
                    IE: Unknown: 07064E4C20010D10
          Cell 11 - Address: 90:5C:44:C5:B8:9D
                    Channel:11
                    Frequency:2.462 GHz (Channel 11)
                    Quality=58/70  Signal level=-52 dBm  
                    Encryption key:on
                    ESSID:"WPAnetwork"
                    Bit Rates:1 Mb/s; 2 Mb/s; 5.5 Mb/s; 11 Mb/s; 9 Mb/s
                              18 Mb/s; 36 Mb/s; 54 Mb/s
                    Bit Rates:6 Mb/s; 12 Mb/s; 24 Mb/s; 48 Mb/s
                    Mode:Master
                    Extra:tsf=000001c683317915
                    Extra: Last beacon: 90ms ago
                    IE: Unknown: 00124368696E6565732052657374617572616E74
                    IE: Unknown: 010882848B961224486C
                    IE: Unknown: 03010B
                    IE: Unknown: 2A0104
                    IE: Unknown: 32040C183060
                    IE: Unknown: 0706455520010D14
                    IE: Unknown: 2D1AAC0117FFFF000000000000000000000000000000000000000000
                    IE: Unknown: 3D160B000700000000000000000000000000000000000000
                    IE: WPA Version 1
                        Group Cipher : TKIP
                        Pairwise Ciphers (2) : TKIP CCMP
                        Authentication Suites (1) : PSK
                    IE: Unknown: 7F080100000000000000
                    IE: Unknown: 0B05040031127A
                    IE: Unknown: DD180050F2020101000003A4000027A4000042435E0062322F00
                    IE: Unknown: 7F080100000000000000
                    IE: Unknown: 0706455520010D10
                    IE: Unknown: DDA70050F204104A0001101044000102103B00010310470010E6825C801DD411B2860188B76881A5BF1021001852616C696E6B20546563686E6F6C6F67792C20436F72702E1023001C52616C696E6B20576972656C6573732041636365737320506F696E74102400065254323836301042000831323334353637381054000800060050F20400011011000952616C696E6B415053100800020000103C0001011049000600372A000120
                    IE: Unknown: DD07000C4300000000
          Cell 12 - Address: 54:FA:3E:60:F9:B1
                    Channel:11
                    Frequency:2.462 GHz (Channel 11)
                    Quality=21/70  Signal level=-89 dBm  
                    Encryption key:on
                    ESSID:"WEP"
                    Bit Rates:1 Mb/s; 2 Mb/s; 5.5 Mb/s; 11 Mb/s; 9 Mb/s
                              18 Mb/s; 36 Mb/s; 54 Mb/s
                    Bit Rates:6 Mb/s; 12 Mb/s; 24 Mb/s; 48 Mb/s
                    Mode:Master
                    Extra:tsf=00000144750d9416
                    Extra: Last beacon: 170ms ago
                    IE: Unknown: 000C485A4E323439303933303637
                    IE: Unknown: 010882848B961224486C
                    IE: Unknown: 03010B
                    IE: Unknown: 2A0104
                    IE: Unknown: 32040C183060
                    IE: Unknown: 2D1AEC0103FFFF0000000000000000000000000000000C0000000000
                    IE: Unknown: 3D160B000100000000000000000000000000000000000000
                    IE: Unknown: DD180050F2020101800003A4000027A4000042435E0062322F00
                    IE: Unknown: 0B05000027127A
                    IE: Unknown: 7F0101
                    IE: Unknown: DD07000C4307000000
                    IE: Unknown: 07064E4C20010D10
                    IE: Unknown: DDA70050F204104A0001101044000102103B00010310470010BC329E001DD811B2860154FA3E60F9B71021001A43656C656E6F20436F6D6D756E69636174696F6E2C20496E632E1023001743656C656E6F20576972656C65737320415020322E344710240006434C313830301042000831323334353637381054000800060050F20400011011000C43656C656E6F4150322E3447100800024388103C0001011049000600372A000120
          Cell 13 - Address: 54:FA:3E:60:F9:B1
                    Channel:11
                    Frequency:2.462 GHz (Channel 11)
                    Quality=21/70  Signal level=-66 dBm  
                    ESSID:"unknown"
                    Bit Rates:1 Mb/s; 2 Mb/s; 5.5 Mb/s; 11 Mb/s; 9 Mb/s
                              18 Mb/s; 36 Mb/s; 54 Mb/s
                    Bit Rates:6 Mb/s; 12 Mb/s; 24 Mb/s; 48 Mb/s
                    Mode:Master
                    Extra:tsf=00000144750d9416
                    Extra: Last beacon: 170ms ago
                    """

class IwlistTests(unittest.TestCase):

    def setUp(self):
        TestLib()
        logging.basicConfig(level=logging.FATAL, format=u'%(asctime)s %(name)s %(levelname)s : %(message)s')
        self.i = Iwlist()

    def tearDown(self):
        pass

    def test_get_networks(self):
        self.i.command = Mock(return_value={
            'returncode': 0,
            'error': False,
            'killed': False,
            'stderr': [],
            'stdout': SAMPLE.split('\n'),
        })
        self.i.get_last_return_code = Mock(return_value=0)

        networks = self.i.get_networks('wlan0')
        logging.debug(pformat(networks))

        self.assertGreaterEqual(len(networks), 1)
        for network in networks:
            net = networks[network]
            self.assertTrue('interface' in net)
            self.assertTrue('network' in net)
            self.assertTrue('encryption' in net)
            self.assertTrue('signallevel' in net)
            self.assertTrue('encryption' in net)
            self.assertTrue('frequencies' in net)

            self.assertTrue(len(net['interface'])>0)
            self.assertTrue(len(net['network'])>0)
            self.assertTrue(isinstance(net['signallevel'], int))
            self.assertTrue(net['encryption'] in (WpaSupplicantConf.ENCRYPTION_TYPE_WPA, WpaSupplicantConf.ENCRYPTION_TYPE_WPA2, WpaSupplicantConf.ENCRYPTION_TYPE_UNSECURED, WpaSupplicantConf.ENCRYPTION_TYPE_WEP, WpaSupplicantConf.ENCRYPTION_TYPE_UNKNOWN))
            self.assertTrue(all(x in (self.i.FREQ_2_4GHZ, self.i.FREQ_5GHZ) for x in net['frequencies']))
            self.assertGreaterEqual(len(net['frequencies']), 1)

    def test_get_networks_failed(self):
        self.i.command = Mock(return_value={
            'returncode': 1,
            'error': False,
            'killed': False,
            'stderr': [],
            'stdout': SAMPLE.split('\n'),
        })
        self.i.get_last_return_code = Mock(return_value=1)

        networks = self.i.get_networks('wlan0')
        logging.debug(pformat(networks))

        self.assertEqual(len(networks), 0, 'Networks list should be empty')

    def test_get_network_cache(self):
        self.i.command = Mock(return_value={
            'returncode': 0,
            'error': False,
            'killed': False,
            'stderr': [],
            'stdout': SAMPLE.split('\n'),
        })
        self.i.get_last_return_code = Mock(return_value=0)

        self.i.get_networks('wlan0')
        self.i.get_networks('wlan0')

        self.assertEqual(self.i.command.call_count, 1)


    def test_has_error(self):
        self.assertTrue(isinstance(self.i.has_error(), bool))

if __name__ == '__main__':
    # coverage run --omit="*/lib/python*/*","*test_*.py" --concurrency=thread test_iwlist.py; coverage report -m -i
    unittest.main()
