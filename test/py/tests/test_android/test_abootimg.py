# SPDX-License-Identifier:  GPL-2.0+
# Copyright (c) 2020
# Author: Sam Protsenko <joe.skb7@gmail.com>

# Test U-Boot's "abootimg" commands.

import os
import pytest
import utils

"""
These tests rely on disk image (boot.img), which is automatically created by
the test from the stored hex dump. This is done to avoid the dependency on the
most recent mkbootimg tool from AOSP/master. Here is the list of commands which
was used to generate the boot.img and obtain compressed hex dump from it:

    $ echo '/dts-v1/; / { model = "x1"; compatible = "y1,z1"; };' > test1.dts
    $ echo '/dts-v1/; / { model = "x2"; compatible = "y2,z2"; };' > test2.dts
    $ dtc test1.dts > dt1.dtb
    $ dtc test2.dts > dt2.dtb
    $ cat dt1.dtb dt2.dtb > dtb.img
    $ echo 'kernel payload' > kernel
    $ echo 'ramdisk payload' > ramdisk.img
    $ mkbootimg --kernel ./kernel --ramdisk ./ramdisk.img  \
                --cmdline "cmdline test" --dtb ./dtb.img   \
                --os_version R --os_patch_level 2019-06-05 \
                --header_version 2 --output boot.img
    $ gzip -9 boot.img
    $ xxd -p boot.img.gz > boot.img.gz.hex

Now one can obtain original boot.img from this hex dump like this:

    $ xxd -r -p boot.img.gz.hex boot.img.gz
    $ gunzip -9 boot.img.gz

For boot image header version 4, these tests rely on two images that are generated
using the same steps above :

1- boot.img :
    $ mkbootimg --kernel ./kernel --ramdisk ./ramdisk.img  \
                --cmdline "cmdline test" --dtb ./dtb.img   \
                --os_version R --os_patch_level 2019-06-05 \
                --header_version 4 --output ./boot.img

2- vendor_boot.img
    $ mkbootimg --kernel ./kernel --ramdisk ./ramdisk.img  \
                --cmdline "cmdline test" --dtb ./dtb.img   \
                --os_version R --os_patch_level 2019-06-05 \
                --pagesize 4096  --vendor_ramdisk ./ramdisk.img \
                --header_version 4 --vendor_boot ./vboot.img \

"""

# boot.img.gz hex dump
img_hex = """1f8b08084844af5d0203626f6f742e696d670073f47309f2f77451e46700
820606010106301084501f04181819041838181898803c3346060c909c9b
92939997aa50925a5cc2300a461c3078b2e1793c4b876fd92db97939fb6c
b7762ffff07d345446c1281805e8a0868d81e117a45e111c0d8dc101b253
8bf25273140a122b73f21353b8460364148c8251300a46c1281801a02831
3725b3387bb401300a46c1281805a360148c207081f7df5b20550bc41640
9c03c41a0c90f17fe85400986d82452b6c3680198a192a0ce17c3610ae34
d4a9820881a70f3873f35352731892f3730b124b32937252a96bb9119ae5
463a5546f82c1f05a360148c8251300a462e000085bf67f200200000"""

# boot img v4 hex dump
boot_img_hex = """1f8b080827b0cd630203626f6f742e696d6700edd8bd0d82601885d1d7c4
58d8c808b88195bd098d8d246e40e42b083f1aa0717be99d003d277916b8
e5bddc8a7b792d8e8788c896ce9b88d32ebe6c971e7ddd3543cae734cd01
c0ffc84c0000b0766d1a87d4e5afeadd3dab7a6f10000000f84163d5d7cd
d43a000000000000000060c53e7544995700400000"""

# vendor boot image v4 hex dump (contains initial bootconfig: androidboot.hardware=test)
vboot_img_hex = """1f8b08000000000002ffeddb316a02411806d009a49040606d3d84374823a9a348b095
915951b2c9caee8690ce237a91406a0b497603e215dcbc577cf3334cf5350303b3787a
9c4fa6d3e7dbf02b6b63dfc6b01b0180ffe726644d5e37975bb34108c76efa1eb65974
c7fed691c600e02a64e7ab3e8494afe37bd128050000007ae6707ffad202000000f45b
155fd3b67e59eee26751c674a711000000e89ff896aa729b5665d98c37b14a1fb1ca1f
da4f7f5e02000000a0377e0040ab5ba000500000"""

# bootable boot image v4 hex dump (contains actual bootable kernel)
boot_bootable_img_hex = """1f8b08081663ee6802ff626f6f745f626f6f7461626c655f76342e696d67
00edd1c14ac3401485e159b80a083ec24dba4f117c81d8140c6dad24ee25
4da6e9d07452321305dfca37d4d4ec5cb954fe6f37ccb967606ef298e6db
2c0d3f94526feae25adda81fae140000000000f8ab66e17c67ecdc1d025d
1d3a89125bf79da9e5beebbc64a7b2d1f27a27cfda7959e9deea369a8263
a0eaecde34e2c75b375495766e3fb46114cca430a7a12dbd96e3654a7663
dfb9f4feeb383514beecbdb1cd1489e3380a5cabf5596ea7c4f78b62acf1
a66ccdbbaea380950100000000f06b79b249b362f5f2b44e16cb87ed3a5d
e67c0a0000000000ffcc27ba944c7e00300000"""

# bootable vendor boot image v4 hex dump (contains actual bootable ramdisk)
vendor_boot_bootable_img_hex = """1f8b08081663ee6802ff76656e646f725f626f6f745f626f6f7461626c65
5f76342e696d6700edd8b10a02310cc6f10c0e7220f8080737b8b93ab9a8
282e571171959e0d787058a84557f5c96ddd7d80c3ff0f92217c5396408e
f56abf30e63090649c9b3c53bd050000fcab57d45b3c35de47db749a06bb
e1eff08c7d0100d00bf6ea826f5dbef0d38b0dee618396f3f27bf69ddedb
b316558a4d462255fe132c4dbdde6e0a160700000000408f7c0027597569
00200000"""

# Expected response for "abootimg dtb_dump" command
dtb_dump_resp="""## DTB area contents (concat format):
 - DTB #0:
           (DTB)size = 125
          (DTB)model = x1
     (DTB)compatible = y1,z1
 - DTB #1:
           (DTB)size = 125
          (DTB)model = x2
     (DTB)compatible = y2,z2"""
# Address in RAM where to load the boot image ('abootimg' looks in $loadaddr)
loadaddr = 0x1000
# Address in RAM where to load the vendor boot image ('abootimg' looks in $vloadaddr)
vloadaddr= 0x10000
# Expected DTB #1 offset from the boot image start address
dtb1_offset = 0x187d
# Expected DTB offset from the vendor boot image start address
dtb2_offset = 0x207d
# DTB #1 start address in RAM
dtb1_addr = loadaddr + dtb1_offset
# DTB #2 start address in RAM
dtb2_addr = vloadaddr + dtb2_offset

class AbootimgTestDiskImage(object):
    """Disk image used by abootimg tests."""

    def __init__(self, ubman, image_name, hex_img):
        """Initialize a new AbootimgDiskImage object.

        Args:
            ubman: A U-Boot console.

        Returns:
            Nothing.
        """

        gz_hex = ubman.config.persistent_data_dir + '/' + image_name  + '.gz.hex'
        gz = ubman.config.persistent_data_dir + '/' + image_name + '.gz'

        filename = image_name
        persistent = ubman.config.persistent_data_dir + '/' + filename
        self.path = ubman.config.result_dir  + '/' + filename
        ubman.log.action('persistent is ' + persistent)
        with utils.persistent_file_helper(ubman.log, persistent):
            if os.path.exists(persistent):
                ubman.log.action('Disk image file ' + persistent +
                    ' already exists')
            else:
                ubman.log.action('Generating ' + persistent)

                f = open(gz_hex, "w")
                f.write(hex_img)
                f.close()
                cmd = ('xxd', '-r', '-p', gz_hex, gz)
                utils.run_and_log(ubman, cmd)
                cmd = ('gunzip', '-9', gz)
                utils.run_and_log(ubman, cmd)

        cmd = ('cp', persistent, self.path)
        utils.run_and_log(ubman, cmd)

gtdi1 = None
@pytest.fixture(scope='function')
def abootimg_disk_image(ubman):
    """pytest fixture to provide a AbootimgTestDiskImage object to tests.
    This is function-scoped because it uses ubman, which is also
    function-scoped. However, we don't need to actually do any function-scope
    work, so this simply returns the same object over and over each time."""

    global gtdi1
    if not gtdi1:
        gtdi1 = AbootimgTestDiskImage(ubman, 'boot.img', img_hex)
    return gtdi1

gtdi2 = None
@pytest.fixture(scope='function')
def abootimgv4_disk_image_vboot(ubman):
    """pytest fixture to provide a AbootimgTestDiskImage object to tests.
    This is function-scoped because it uses ubman, which is also
    function-scoped. However, we don't need to actually do any function-scope
    work, so this simply returns the same object over and over each time."""

    global gtdi2
    if not gtdi2:
        gtdi2 = AbootimgTestDiskImage(ubman, 'vendor_boot.img', vboot_img_hex)
    return gtdi2

gtdi3 = None
@pytest.fixture(scope='function')
def abootimgv4_disk_image_boot(ubman):
    """pytest fixture to provide a AbootimgTestDiskImage object to tests.
    This is function-scoped because it uses ubman, which is also
    function-scoped. However, we don't need to actually do any function-scope
    work, so this simply returns the same object over and over each time."""

    global gtdi3
    if not gtdi3:
        gtdi3 = AbootimgTestDiskImage(ubman, 'bootv4.img', boot_img_hex)
    return gtdi3

gtdi4 = None
@pytest.fixture(scope='function')
def abootimgv4_bootable_disk_image_boot(ubman):
    """pytest fixture to provide bootable boot image v4."""
    global gtdi4
    if not gtdi4:
        gtdi4 = AbootimgTestDiskImage(ubman, 'boot_bootable_v4.img', boot_bootable_img_hex)
    return gtdi4

gtdi5 = None
@pytest.fixture(scope='function')
def abootimgv4_bootable_disk_image_vboot(ubman):
    """pytest fixture to provide bootable vendor boot image v4."""
    global gtdi5
    if not gtdi5:
        gtdi5 = AbootimgTestDiskImage(ubman, 'vendor_boot_bootable_v4.img', vendor_boot_bootable_img_hex)
    return gtdi5

@pytest.mark.boardspec('sandbox')
@pytest.mark.buildconfigspec('android_boot_image')
@pytest.mark.buildconfigspec('cmd_abootimg')
@pytest.mark.buildconfigspec('cmd_fdt')
@pytest.mark.requiredtool('xxd')
@pytest.mark.requiredtool('gunzip')
def test_abootimg(abootimg_disk_image, ubman):
    """Test the 'abootimg' command."""

    ubman.log.action('Loading disk image to RAM...')
    ubman.run_command('setenv loadaddr 0x%x' % (loadaddr))
    ubman.run_command('host load hostfs - 0x%x %s' % (loadaddr,
        abootimg_disk_image.path))

    ubman.log.action('Testing \'abootimg get ver\'...')
    response = ubman.run_command('abootimg get ver')
    assert response == "2"
    ubman.run_command('abootimg get ver v')
    response = ubman.run_command('env print v')
    assert response == 'v=2'

    ubman.log.action('Testing \'abootimg get recovery_dtbo\'...')
    response = ubman.run_command('abootimg get recovery_dtbo a')
    assert response == 'Error: recovery_dtbo_size is 0'

    ubman.log.action('Testing \'abootimg dump dtb\'...')
    response = ubman.run_command('abootimg dump dtb').replace('\r', '')
    assert response == dtb_dump_resp

    ubman.log.action('Testing \'abootimg get dtb_load_addr\'...')
    ubman.run_command('abootimg get dtb_load_addr a')
    response = ubman.run_command('env print a')
    assert response == 'a=11f00000'

    ubman.log.action('Testing \'abootimg get dtb --index\'...')
    ubman.run_command('abootimg get dtb --index=1 dtb1_start')
    response = ubman.run_command('env print dtb1_start')
    correct_str = "dtb1_start=%x" % (dtb1_addr)
    assert response == correct_str
    ubman.run_command('fdt addr $dtb1_start')
    ubman.run_command('fdt get value v / model')
    response = ubman.run_command('env print v')
    assert response == 'v=x2'

@pytest.mark.boardspec('sandbox')
@pytest.mark.buildconfigspec('android_boot_image')
@pytest.mark.buildconfigspec('cmd_abootimg')
@pytest.mark.buildconfigspec('cmd_fdt')
@pytest.mark.requiredtool('xxd')
@pytest.mark.requiredtool('gunzip')
def test_abootimgv4(abootimgv4_disk_image_vboot, abootimgv4_disk_image_boot, ubman):
    """Test the 'abootimg' command with boot image header v4."""

    ubman.log.action('Loading disk image to RAM...')
    ubman.run_command('setenv loadaddr 0x%x' % (loadaddr))
    ubman.run_command('setenv vloadaddr 0x%x' % (vloadaddr))
    ubman.run_command('host load hostfs - 0x%x %s' % (vloadaddr,
	abootimgv4_disk_image_vboot.path))
    ubman.run_command('host load hostfs - 0x%x %s' % (loadaddr,
        abootimgv4_disk_image_boot.path))
    ubman.run_command('abootimg addr 0x%x 0x%x' % (loadaddr, vloadaddr))
    ubman.log.action('Testing \'abootimg get ver\'...')
    response = ubman.run_command('abootimg get ver')
    assert response == "4"
    ubman.run_command('abootimg get ver v')
    response = ubman.run_command('env print v')
    assert response == 'v=4'

    ubman.log.action('Testing \'abootimg get recovery_dtbo\'...')
    response = ubman.run_command('abootimg get recovery_dtbo a')
    assert response == 'Error: header version must be >= 1 and <= 2 to get dtbo'

    ubman.log.action('Testing \'abootimg get dtb_load_addr\'...')
    ubman.run_command('abootimg get dtb_load_addr a')
    response = ubman.run_command('env print a')
    assert response == 'a=11f00000'

    ubman.log.action('Testing \'abootimg get dtb --index\'...')
    ubman.run_command('abootimg get dtb --index=1 dtb2_start')
    response = ubman.run_command('env print dtb2_start')
    correct_str = "dtb2_start=%x" % (dtb2_addr)
    assert response == correct_str

    ubman.run_command('fdt addr $dtb2_start')
    ubman.run_command('fdt get value v / model')
    response = ubman.run_command('env print v')
    assert response == 'v=x2'

@pytest.mark.boardspec('sandbox')
@pytest.mark.buildconfigspec('android_boot_image')
@pytest.mark.buildconfigspec('cmd_abootimg')
@pytest.mark.requiredtool('xxd')
@pytest.mark.requiredtool('gunzip')
def test_abootimg_bootconfig(abootimgv4_disk_image_vboot,
                              abootimgv4_disk_image_boot,
                              ubman):
    """Test bootconfig handling with boot image v4.

    Verifies that androidboot.* parameters from bootargs are appended to the
    bootconfig section in vendor_boot image in memory, and that non-androidboot
    parameters remain in bootargs.
    """

    # Setup addresses
    ram_base = utils.find_ram_base(ubman)
    ramdisk_addr_r = ram_base + 0x4000000
    ubman.run_command('setenv ramdisk_addr_r 0x%x' % ramdisk_addr_r)
    ubman.run_command('setenv loadaddr 0x%x' % loadaddr)
    ubman.run_command('setenv vloadaddr 0x%x' % vloadaddr)

    # Set bootargs with androidboot.* parameters
    ubman.run_command('setenv bootargs "androidboot.serialno=ABC123 androidboot.mode=recovery console=ttyS0"')

    # Load images
    ubman.run_command('host load hostfs - 0x%x %s' % (vloadaddr,
        abootimgv4_disk_image_vboot.path))
    ubman.run_command('host load hostfs - 0x%x %s' % (loadaddr,
        abootimgv4_disk_image_boot.path))
    ubman.run_command('abootimg addr 0x%x 0x%x' % (loadaddr, vloadaddr))

    # Extract ramdisk (triggers bootconfig append)
    ubman.run_command('abootimg get ramdisk ramdisk_addr ramdisk_size')

    # Get ramdisk address
    response = ubman.run_command('env print ramdisk_addr')
    ramdisk_start = int(response.split('=')[1], 16)

    # Verify androidboot.* parameters were removed from bootargs
    response = ubman.run_command('env print bootargs')
    assert 'androidboot.' not in response
    assert 'console=ttyS0' in response

    # Get ramdisk size and verify BOOTCONFIG magic at the end
    response = ubman.run_command('env print ramdisk_size')
    ramdisk_size = int(response.split('=')[1], 16)

    # Dump the end of the ramdisk where BOOTCONFIG trailer should be
    response = ubman.run_command('md.b 0x%x 96' % (ramdisk_start))

    # Verify BOOTCONFIG magic is present
    assert 'BOOTCONFIG' in response or 'BOOTCON' in response
