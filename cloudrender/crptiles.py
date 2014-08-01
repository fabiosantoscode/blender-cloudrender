import math

def tiles_from_crowdprocess(job, viewport_tiles):
    tiles_to_go = set(viewport_tiles)

    retries = int(math.sqrt(len(tiles_to_go)) + 5)

    for retry in range(retries):
        if not tiles_to_go:
            break

        if retry > 0:
            print('Retrying %d tiles... %dth try' % (len(tiles_to_go), retry))

        job_data = (
            { 'x': x, 'y': y, 'w': w, 'h': h }
            for x, y, w, h in tiles_to_go)

        for tile in job(list(job_data)).results:
            tile_data = (tile['x'], tile['y'],
                tile['w'], tile['h'])
            if tile_data not in tiles_to_go:
                print('???? We\'ve already rendered this tile: %r' % tile_data)
                continue

            tiles_to_go.remove(tile_data)

            yield tile, tile_data

            if not tiles_to_go:
                break
