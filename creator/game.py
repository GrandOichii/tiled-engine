import json
import os
import os.path as path

CHARS = [chr(i) for i in range(ord('a'), ord('z')+1)] + [chr(i) for i in range(ord('A'), ord('Z')+1)] + [chr(i) for i in range(ord('0'), ord('9')+1)]

def script_path(tile):
    return path.join('scripts', f'{tile.name}_script.lua')

class Tile:
    def __init__(self) -> None:
        self.name: str = ''
        self.display_name: str = ''
        self.seethrough: bool = False
        self.passable: bool = False

        self.script: str = ''
        self.step_func: str = ''
        self.interact_func: str = ''

        self.image = None
        self.image_path: str = None

    def to_json(self) -> dict:
        result = {}
        result['name'] = self.name
        result['display_name'] = self.display_name
        result['passable'] = self.passable
        result['seethrough'] = self.seethrough
        if self.script != '':
            events = {}
            events['script'] = script_path(self)
            if self.step_func != '':
                events['step'] = self.step_func
            if self.interact_func != '':
                events['interact'] = self.interact_func
            result['events'] = events
        return result

    def copy(self, other: 'Tile'):
        self.__dict__ = other.__dict__

class Room:
    def __init__(self) -> None:
        self.name: lambda: str = None
        self.tileset: list[Tile] = []
        self.layout: list[list[Tile]] = []

    def save(self, dir: str):
        p = path.join(dir, f'{self.name()}.json')
        j = {}
        tilesets_j = {}
        d = {}
        i = 0
        for tile in self.tileset:
            cc = CHARS[i]
            d[tile] = cc
            tilesets_j[cc] = tile.to_json()
            i += 1
            open(path.join(dir, script_path(tile)), 'w').write(tile.script)

        j['tileset'] = tilesets_j

        layout_j = ''
        height = len(self.layout)
        width = len(self.layout[0])
        for i in range(height):
            for ii in range(width):
                layout_j += d[self.layout[ii][i]]
            layout_j += '\n'

        j['layout'] = layout_j

        open(p, 'w').write(json.dumps(j, indent=4))
        return None

    def can_save(self):
        for i in range(len(self.layout)):
            for j in range(len(self.layout[i])):
                if self.layout[i][j] is None:
                    return f'Tile at ({j}, {i}) is not set at room {self.name()}'
        return None

class Game:
    def __init__(self) -> None:
        self.name: lambda: str = None
        self.description: lambda: str = None
        self.project_name: lambda: str = None

        self.spawn_room: Room = None
        self.spawn_x_loc: lambda: int = None
        self.spawn_y_loc: lambda: int = None
        
        self.rooms: list[Room] = list()

    def exists_room_with_name(self, name: str):
        for r in self.rooms:
            if r.name() == name:
                return True
        return False

    def save(self, p: str) -> None|str:
        project_name = self.project_name()
        if project_name is None:
            return 'No project name specified'

        name = self.name()
        if name == '':
            return 'No game name specified'
        
        if self.spawn_room is None:
            return 'No starting room specified'

        if self.spawn_x_loc is None or self.spawn_x_loc() < 0:
            return 'Spawn X location not specified'
        if self.spawn_y_loc is None or self.spawn_x_loc() < 0:
            return 'Spawn Y location not specified'

        j = {}
        j['name'] = name
        j['project_name'] = project_name
        j['description'] = self.description()
        spawn_j = {}
        spawn_j['room_name'] = self.spawn_room.name()
        spawn_j['x_loc'] = self.spawn_x_loc()
        spawn_j['y_loc'] = self.spawn_y_loc()
        j['spawn'] = spawn_j

        for r in self.rooms:
            err = r.can_save()
            if err is not None:
                return err
                
        os.makedirs(p, exist_ok=True)
        rooms_p = path.join(p, 'rooms')
        os.makedirs(rooms_p, exist_ok=True)
        rooms_j = {}
        for r in self.rooms:
            os.makedirs(path.join(rooms_p, 'scripts'), exist_ok=True)
            err = r.save(rooms_p)
            if err is not None:
                return err
            r_name = r.name()
            rooms_j[r_name] = path.join('rooms', f'{r_name}.json')
        j['rooms'] = rooms_j

        open(path.join(p, 'manifest.json'), 'w').write(json.dumps(j, indent=4))

    def load(dir: str):
        result = Game()
        game_info = json.loads(open(path.join(dir, 'manifest.json'), 'r').read())
        spawn = game_info['spawn']

        result.temp_name = game_info['name']
        result.temp_description = game_info['description']
        result.temp_project_name = game_info['project_name']

        result.spawn_temp_x_loc = spawn['x_loc']
        result.spawn_temp_y_loc = spawn['x_loc']

        rooms_j = game_info['rooms']
        for room_name, rpath in rooms_j.items():

            room_path = path.join(dir, rpath)
            room_data = json.loads(open(room_path, 'r').read())
            room = Room()
            room.temp_name = room_name
            actual_d = {}
            # construct tileset
            for tile_c, tile_j in room_data['tileset'].items():
                tile = Tile()
                tile.name = tile_j['name']
                tile.display_name = tile_j['display_name']
                tile.seethrough = tile_j['seethrough']
                tile.passable = tile_j['passable']
                tile.image_path = 'error.png'
                if 'image_path' in tile_j:
                    tile.image_path = tile_j['image_path']
                if 'events' in tile_j:
                    events = tile_j['events']
                    tile.script = open(path.join(path.dirname(room_path), events['script']), 'r').read()
                    if 'interact' in events:
                        tile.interact_func = events['interact']
                    if 'step' in events:
                        tile.step_func = events['step']
                actual_d[tile_c] = tile
                room.tileset += [tile]
            # fill layout
            for row in room_data['layout'].split('\n'):
                if row == '': continue
                r = []
                for c in row:
                    r += [actual_d[c]]
                room.layout += [r]
            # add room to list
            result.rooms += [room]
            # set spawn room
            if room_name == spawn['room_name']:
                result.spawn_room = room

        return result