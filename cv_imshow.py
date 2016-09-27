# Copyright (c) 2012, Renato Florentino Garcia <fgarcia.renato@gmail.com>
#                     Stefano Pellegrini <stefpell@ee.ethz.ch>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the authors nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHORS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import gdb
from PIL import Image
import pylab as pl
import struct
import numpy as np


def get_next_variable_name(var_name):
    print('Looking for delimiters in ', var_name)
    pos1 = var_name.find('.')
    pos2 = var_name.find('->')
    pos3 = var_name.find('[')
    print(pos1, ' ', pos2, ' ', pos3)
    if(pos1 == 0):
        pos1 = var_name[1:].find('.')
        if(pos1 != -1):
            pos1 = pos1 + 1
        print(pos1)
    if(pos2 == 0):
        pos2 = var_name[2:].find('->') + 2
    if(pos3 == 0):
        pos3 = var_name[1:].find('[') + 1

    if(pos1 == -1 and pos2 == -1 and pos3 == -1):
        print('Did not find any delimiters in ', var_name)
        return [var_name, '']
    if(pos1 == -1):
        pos1 = len(var_name) + 1
    if(pos2 == -1):
        pos2 = len(var_name) + 1
    if(pos3 == -1):
        pos3 = len(var_name) + 1

    print(pos1, ' ', pos2, ' ', pos3)
    if(pos1 < pos2 and pos1 < pos3):
        print('Delimiter \'.\' found at ', pos1)
        return [var_name[0:pos1], var_name[pos1:]]
    if(pos2 < pos1 and pos2 < pos3):
        print('Delimiter \'->\' found at ', pos2)
        return [var_name[0:pos2], var_name[pos2:]]
    if(pos3 < pos1 and pos3 < pos2):
        print('Delimiter \'[\' found at ', pos3)
        return [var_name[0:pos3], var_name[pos3:]]

def index_container(container, index):
    if(str(container.type).find('std::vector') == 0):
        idx_pos = index.find(']')
        idx = int(index[0:idx_pos])
        obj = (container['_M_impl']['_M_start'] + idx).dereference()
        return obj, index[idx_pos+1:]



def get_mat_helper(var_name, variable):
    if(str(variable.type).find('cv::Mat') == 0):
        return variable
    print('Mat not found, attempting to find delimiters')
    # find the next deliminating element
    var_name, rest = get_next_variable_name(var_name)

    print('Split var name to ', var_name, ' and ', rest)
    if(var_name[0] == '.'):
        variable = variable[var_name[1:]]
    elif(var_name[0:2] == '->'):
        variable = variable[var_name[2:]]
    if(len(rest) == 0):
        return variable
    if(rest[0] == '.'):
        return get_mat_helper(rest[1:], variable)
    if(rest[0:2] == '->'):
        return get_mat_helper(rest[2:], variable)
    if(rest[0] == '['):
        variable, rest = index_container(variable, rest[1:])
        return get_mat_helper(rest, variable)


def get_mat(var_name, frame):
    print('Looking for cv::Mat named ', var_name, ' in frame ', frame.name())
    tmp_var_name, rest = get_next_variable_name(var_name)
    print('Split var name to ', var_name, ' and ', rest)
    try_this = False
    try:
        var = frame.read_var(tmp_var_name)
    except ValueError:
        try_this = True
    if(try_this):
        var = frame.read_var('this')
        var = var[tmp_var_name]
    return get_mat_helper(rest, var)


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

class cv_closeAll(gdb.Command):
    def __init__(self):
        super(cv_closeAll, self).__init__('cv_closeAll', gdb.COMMAND_SUPPORT, gdb.COMPLETE_FILENAME)

    def invoke(self, arg, from_tty):
        pl.close('all')

def handle_container(container, index, i):
    if( str(container.type).find('std::vector') == 0):
        obj = (container['_M_impl']['_M_start'] + int(index[i])).dereference()
        return handle_container(obj, index, i+1)
    if(str(container.type).find('cv::Mat') == 0):
        return container


class cv_printMat(gdb.Command):
    def __init__(self):
        super(cv_printMat, self).__init__('cv_printMat', gdb.COMMAND_SUPPORT, gdb.COMPLETE_FILENAME)

    def invoke(self, arg, from_tty):
        # Access the variable from gdb.
        frame = gdb.selected_frame()
        val = get_mat(arg, frame)

        flags = val['flags']
        depth = flags & 7
        channels = 1 + (flags >> 3) & 63;
        rows = val['rows']
        cols = val['cols']
        line_step = val['step']['p'][0]
        data_address = val['data']
        infe = gdb.inferiors()
        memory_data = infe[0].read_memory(data_address, line_step * rows)
        print('Matrix with rows: ', rows, ' cols: ', cols, ' channels: ', channels)
        if depth == 0:
            print( np.frombuffer(memory_data, dtype='uint8').reshape((rows,cols,channels)) )
        elif depth == 1:
            print( np.frombuffer(memory_data, dtype='int8').reshape((rows,cols,channels)) )
        elif depth == 2:
            print( np.frombuffer(memory_data, dtype='uint16').reshape((rows,cols,channels)) )
        elif depth == 3:
            print( np.frombuffer(memory_data, dtype='int16').reshape((rows,cols,channels)) )
        elif depth == 4:
            print( np.frombuffer(memory_data, dtype='int32').reshape((rows,cols,channels)) )
        elif depth == 5:
            print( np.frombuffer(memory_data, dtype='float32').reshape((rows,cols,channels)) )
        elif depth == 6:
            print( np.frombuffer(memory_data, dtype='float64').reshape((rows,cols,channels)) )
        else:
            gdb.write('Unsupported cv::Mat depth\n', gdb.STDERR)
            return

class cv_imshow(gdb.Command):
    """Diplays the content of an opencv image"""

    def __init__(self):
        super(cv_imshow, self).__init__('cv_imshow',
                                        gdb.COMMAND_SUPPORT,
                                        gdb.COMPLETE_FILENAME)

    def invoke (self, arg, from_tty):
        pos = arg.find(' ')
        flag = ''
        if(pos != -1):
            arg, flag = arg.split(' ')

        # Access the variable from gdb.
        frame = gdb.selected_frame()

        val = get_mat(arg, frame)

        if str(val.type.strip_typedefs()) == 'IplImage *':
            img_info = self.get_iplimage_info(val)
        else:
            img_info = self.get_cvmat_info(val)

        if img_info: self.show_image(arg, flag, *img_info)

    @staticmethod
    def get_cvmat_info(val):
        flags = val['flags']
        depth = flags & 7
        channels = 1 + (flags >> 3) & 63;
        if depth == 0:
            cv_type_name = 'CV_8U'
            data_symbol = 'B'
        elif depth == 1:
            cv_type_name = 'CV_8S'
            data_symbol = 'b'
        elif depth == 2:
            cv_type_name = 'CV_16U'
            data_symbol = 'H'
        elif depth == 3:
            cv_type_name = 'CV_16S'
            data_symbol = 'h'
        elif depth == 4:
            cv_type_name = 'CV_32S'
            data_symbol = 'i'
        elif depth == 5:
            cv_type_name = 'CV_32F'
            data_symbol = 'f'
        elif depth == 6:
            cv_type_name = 'CV_64F'
            data_symbol = 'd'
        else:
            gdb.write('Unsupported cv::Mat depth\n', gdb.STDERR)
            return

        rows = val['rows']
        cols = val['cols']

        line_step = val['step']['p'][0]

        gdb.write(cv_type_name + ' with ' + str(channels) + ' channels, ' +
                  str(rows) + ' rows and ' +  str(cols) +' cols\n')

        data_address = val['data']


        return (cols, rows, channels, line_step, data_address, data_symbol)

    @staticmethod
    def get_iplimage_info(val):
        depth = val['depth']
        channels = val['nChannels']
        if depth == 0x8:
            cv_type_name = 'IPL_DEPTH_8U'
            data_symbol = 'B'
            elem_size = 1
        elif depth == -0x7FFFFFF8:
            cv_type_name = 'IPL_DEPTH_8S'
            data_symbol = 'b'
            elem_size = 1
        elif depth == 0x10:
            cv_type_name = 'IPL_DEPTH_16U'
            data_symbol = 'H'
            elem_size = 2
        elif depth == -0x7FFFFFF0:
            cv_type_name = 'IPL_DEPTH_16S'
            data_symbol = 'h'
            elem_size = 2
        elif depth == -0x7FFFFFE0:
            cv_type_name = 'IPL_DEPTH_32S'
            data_symbol = 'i'
            elem_size = 4
        elif depth == 0x20:
            cv_type_name = 'IPL_DEPTH_32F'
            data_symbol = 'f'
            elem_size = 4
        elif depth == 0x40:
            cv_type_name = 'IPL_DEPTH_64F'
            data_symbol = 'd'
            elem_size = 8
        else:
            gdb.write('Unsupported IplImage depth\n', gdb.STDERR)
            return

        rows = val['height'] if str(val['roi']) == '0x0' else val['roi']['height']
        cols = val['width'] if str(val['roi']) == '0x0' else val['roi']['width']
        line_step = val['widthStep']

        gdb.write(cv_type_name + ' with ' + str(channels) + ' channels, ' +
                  str(rows) + ' rows and ' +  str(cols) +' cols\n')

        data_address = unicode(val['imageData']).encode('utf-8').split()[0]
        data_address = int(data_address, 16)
        if str(val['roi']) != '0x0':
            x_offset = int(val['roi']['xOffset'])
            y_offset = int(val['roi']['yOffset'])
            data_address += line_step * y_offset + x_offset * elem_size * channels

        return (cols, rows, channels, line_step, data_address, data_symbol)


    @staticmethod
    def show_image(name, flag, width, height, n_channel, line_step, data_address, data_symbol):
        """ Copies the image data to a PIL image and shows it.

        Args:
            width: The image width, in pixels.
            height: The image height, in pixels.
            n_channel: The number of channels in image.
            line_step: The offset to change to pixel (i+1, j) being
                in pixel (i, j), in bytes.
            data_address: The address of image data in memory.
            data_symbol: Python struct module code to the image data type.
        """

        width = int(width)
        height = int(height)
        n_channel = int(n_channel)
        line_step = int(line_step)
        data_address = int(data_address)

        infe = gdb.inferiors()
        memory_data = infe[0].read_memory(data_address, line_step * height)

        # Calculate the memory padding to change to the next image line.
        # Either due to memory alignment or a ROI.
        if data_symbol in ('b', 'B'):
            elem_size = 1
        elif data_symbol in ('h', 'H'):
            elem_size = 2
        elif data_symbol in ('i', 'f'):
            elem_size = 4
        elif data_symbol == 'd':
            elem_size = 8
        padding = line_step - width * n_channel * elem_size

        # Format memory data to load into the image.
        image_data = []
        if n_channel == 1:
            mode = 'L'
            fmt = '%d%s%dx' % (width, data_symbol, padding)
            for line in chunker(memory_data, line_step):
                image_data.extend(struct.unpack(fmt, line))
        elif n_channel == 3:
            mode = 'RGB'
            fmt = '%d%s%dx' % (width * 3, data_symbol, padding)
            for line in chunker(memory_data, line_step):
                image_data.extend(struct.unpack(fmt, line))
        else:
            gdb.write('Only 1 or 3 channels supported\n', gdb.STDERR)
            return

        scale_alpha = 1
        scale_beta  = 0
        # Fit the opencv elemente data in the PIL element data
        if data_symbol == 'b':
            image_data = [i+128 for i in image_data]
        elif data_symbol == 'H':
            image_data = [i>>8 for i in image_data]
        elif data_symbol == 'h':
            image_data = [(i+32768)>>8 for i in image_data]
        elif data_symbol == 'i':
            image_data = [(i+2147483648)>>24 for i in image_data]
        elif data_symbol in ('f','d'):
            # A float image is discretized in 256 bins for display.
            max_image_data = max(image_data)
            min_image_data = min(image_data)
            img_range = max_image_data - min_image_data
            if img_range > 0:
                scale_beta = min_image_data
                scale_alpha = img_range / 255.0
                image_data = [int(255 * (i - min_image_data) / img_range) \
                              for i in image_data]
            else:
                image_data = [0 for i in image_data]
        
        dump_data = []
        if n_channel == 3:
            for i in range(0, len(image_data), 3):
                dump_data.append((image_data[i+2], image_data[i+1], image_data[i]))
        if n_channel == 1:
            dump_data = image_data

        # Show image.
        if n_channel == 1:
            img = Image.new(mode, (width, height))
        if n_channel == 3:
            img = Image.new(mode, (width, height), color=(0,0,0))

        #img = np.reshape(dump_data, (height,width,n_channel)).astype(np.uint8)
        #print(img.shape)
        #cv2.imshow('image', img)
        #cv2.waitKey(0)

        img.putdata(dump_data)
        img = pl.asarray(img);

        fig = pl.figure()
        fig.canvas.set_window_title(name)
        b = fig.add_subplot(111)


        if n_channel == 1:
            b.imshow(img, cmap = pl.cm.Greys_r, interpolation='nearest')
        elif n_channel == 3:
            b.imshow(img, interpolation='nearest')

        def format_coord(x, y):
            col = int(x+0.5)
            row = int(y+0.5)
            if col>=0 and col<width and row>=0 and row<height:
                if n_channel == 1:
                    z = img[row,col] * scale_alpha + scale_beta
                    return '(%d, %d), [%1.2f]'%(col, row, z)
                elif n_channel == 3:
                    z0 = img[row,col,0] * scale_alpha + scale_beta
                    z1 = img[row,col,1] * scale_alpha + scale_beta
                    z2 = img[row,col,2] * scale_alpha + scale_beta
                    return '(%d, %d), [%1.2f, %1.2f, %1.2f]'%(col, row, z0, z1, z2)
            else:
                return 'x=%d, y=%d'%(col, row)

        b.format_coord = format_coord
        if(flag == 'block'):
            pl.show(block=True)
        else:
            pl.show(block=False)

cv_imshow()
cv_closeAll()
cv_printMat()
