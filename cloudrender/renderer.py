import threading
from queue import Queue
from io import StringIO
from . import crptiles
from .xml_exporter.io_scene_cycles import export_cycles
import imp
from os import path
import json
import zlib
import base64

def viewport_columns(width, size=10):
    for i in range(0, width, size):
        if i + size > width:
            yield i, width - i
        else:
            yield i, size

def viewport_divisions(height, width, bucket_height=64, bucket_width=64):
    assert height > 0 and width > 0 and bucket_height > 0 and bucket_width > 0

    for y in range(0, height, bucket_height):
        for x, col_width in viewport_columns(width, bucket_width):
            last = y + bucket_height
            if y + bucket_height > height:
                yield (x, y, col_width, height - y)
            else:
                yield (x, y, col_width, bucket_height)


class Renderer():
    def iter_tiles(self):
        if self.iterating:
            raise TypeError('Cannot call iter_tiles() more than once '
                'for each Renderer instance')
        self.iterating = True
        for x in range(len(self.divisions)):
            yield self._queue.get()

    def __init__(self, scene, crp):
        fp = StringIO()

        export_cycles.export_cycles(
            fp=fp, scene=scene, inline_textures=True)
        self.scene_xml = fp.getvalue()

        self._queue = Queue()
        self.crp = crp
        self.done = False
        self.iterating = False
        self.running = False

        resolution_fraction = (100 / scene.render.resolution_percentage)
        self.height, self.width = (
            int(scene.render.resolution_y / resolution_fraction),
            int(scene.render.resolution_x / resolution_fraction),
        )

        self.divisions = list(viewport_divisions(
            height=self.height,
            width=self.width,
            bucket_height=scene.render.tile_y,
            bucket_width=scene.render.tile_x))


    def run(self):
        if self.running:
            raise ValueError('Can only run() a Renderer once!')
        self.running = True

        job = self.make_job()

        tiles = crptiles.tiles_from_crowdprocess(job, self.divisions)

        for tile, tile_rect in tiles:
            tile_data = base64.b64decode(tile['tile'])

            if tile['deflated'] == True:
                tile_data = zlib.decompress(tile_data)

            self._queue.put((tile_rect, tile_data))

        self.done = True

        job.delete()

    def run_async(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        return thread

    def make_job(self):
        imp.reload(export_cycles)

        emcycles_core = open(path.join(path.dirname(__file__),
            'emcycles/cloudrender_core.js')).read()

        pako = open(path.join(path.dirname(__file__),
            'pako_deflate.js')).read()

        crowdprocess_func = func_template % (
            json.dumps(self.scene_xml),
            emcycles_core,
            pako,
            base_64_enc)

        # open('/tmp/wow.js', 'w').write(crowdprocess_func)

        return self.crp.job(crowdprocess_func)

func_template = '''
function Run(data) {
    var console = {
        log: function(){},
        error: function(){},
        warn: function(){},
        time: function(){},
        timeEnd: function(){},
        assert: function(){}
    };
    var Module = {
        print: function () {},
        tileX: data.x,
        tileY: data.y,
        tileH: data.h,
        tileW: data.w
    }

    var SCENE = %s;  // scene_xml
    var INCLUDES = [];

    ;%s;  // emcycles

    data.tile = Module.imageData

    ;%s;  // pako

    ;%s;  // base64

    var deflated = pako.deflate(data.tile)

    if (deflated.length < data.tile.length) {
        data.tile = deflated
        data.deflated = true
    }
    data.tile = base64(data.tile)

    return data
}
'''

base_64_enc = '''
// From: http://www.webtoolkit.info/
function base64(input) {
  var keyStr = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=";
  var output = "";
  var chr1, chr2, chr3, enc1, enc2, enc3, enc4;
  var i = 0;

  while (i < input.length) {
    chr1 = input[i++];
    chr2 = input[i++];
    chr3 = input[i++];

    enc1 = chr1 >> 2;
    enc2 = ((chr1 & 3) << 4) | (chr2 >> 4);
    enc3 = ((chr2 & 15) << 2) | (chr3 >> 6);
    enc4 = chr3 & 63;

    if (isNaN(chr2)) {
      enc3 = enc4 = 64;
    } else if (isNaN(chr3)) {
      enc4 = 64;
    }

    output = output +
      keyStr.charAt(enc1) + keyStr.charAt(enc2) +
      keyStr.charAt(enc3) + keyStr.charAt(enc4);
  }

  return output;
}
'''
