#!/usr/bin/python
from dumper import *

def qform__cv__Mat():
    return "Normal,Displayed"

def qdump__cv__Mat(d, value):
    cols = value["cols"]
    rows = value["rows"]
    flags = value["flags"]
    depth = flags & 7
    channels = 1 + (flags >> 3) & 63
    line_step = value['step']['p'][0]

    if depth == 0:
        d.putValue("(%dx%dx%d) CV_8U" %(rows,cols,channels))
    if depth == 1:
        d.putValue("(%dx%dx%d) CV_8S" %(rows,cols,channels))
    if depth == 2:
        d.putValue("(%dx%dx%d) CV_16U" %(rows,cols,channels))

    if depth == 3:
        d.putValue("(%dx%dx%d) CV_16S" %(rows,cols,channels))

    if depth == 4:
        d.putValue("(%dx%dx%d) CV_32S" %(rows,cols,channels))

    if depth == 5:
        d.putValue("(%dx%dx%d) CV_32F" %(rows,cols,channels))

    if depth == 6:
        d.putValue("(%dx%dx%d) CV_64F" %(rows,cols,channels))

    line_step = value['step']['p'][0]
    data_start = value['data']
    #data_start = d.extractPointer(d.addressOf(value['datatstart']))
    data_end = value['dataend']
    nbytes = data_end - data_start
    nbytes = rows * cols * channels
    d.putNumChild(1)
    padding = line_step - cols * channels

    bits = gdb.Value(data_start.cast(value['data'].type.pointer()))
    with Children(d):
       d.putSubItem("Data start", data_start)
       d.putSubItem("Rows", rows)
       d.putSubItem("Cols", cols)
       d.putSubItem("Channels", channels)
       d.putSubItem("Depth", depth)
       d.putSubItem("Num Bytes", nbytes)
       d.putSubItem("Data end", data_end)
       d.putSubItem("Row Step", line_step)
       d.putSubItem("Padding", padding)
       with SubItem(d, "data"):
           d.putValue("0x%x" % bits)
           d.putNumChild(0)
           d.putType("void *")
    format = d.currentItemFormat()
    if format == 1:
        d.putDisplay(StopDisplay)
    if format == 2:
        #file = tempfile.mkstemp(prefix="gdbpy_")
        #filename = file[1].replace("\\", "\\\\")
        #gdb.execute("dump binary memory %s %s %s" % (filename, bits, bits + nbytes))
        #d.putDisplay(DisplayImageFile, " %d %d %d %d %s" % (cols, rows, nbytes, channels, filename))
        d.putField("editformat", DisplayImageData)
        d.put('editvalue="')
        d.put('%08x%08x%08x%08x' % (cols, rows, nbytes, channels))
        d.put(d.readMemory(bits,nbytes))
        d.put('",')

