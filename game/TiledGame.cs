using Newtonsoft.Json;
using Newtonsoft.Json.Serialization;
using Tiled.Layout;
using NLua;
using System.Linq.Expressions;
using System.Reflection;

namespace Tiled {
    public delegate bool TileSelector(TileSlot t);
    public class TiledGame
    {
        private static string MANIFEST_FILE = "manifest.json";

        public string Name { get; }
        public string Description { get; }

        private Dictionary<string, Room> _rooms;
        public Room CurrentRoom { get; set; }

        public Lua LState { get; } = new();

        #region Window info
        private int _windowWidth;
        private int _windowHeight;
        private int _wCenterX;
        private int _wCenterY;
        #endregion

        public static TiledGame Load(string path)
        {

            #region Manifest Reading
            var mPath = Path.Combine(path, MANIFEST_FILE);
            if (!File.Exists(mPath)) throw new Exception(MANIFEST_FILE + " file not found in " + path);
            string mText = File.ReadAllText(mPath);
            var manifest = JsonConvert.DeserializeObject<JManifest>(mText);
            if (manifest is null) throw new Exception("Failed to parse " + MANIFEST_FILE + ": " + mText);
            TiledGame result = new TiledGame(manifest.Name, manifest.Description);
            #endregion
            #region Room Loading
            result._rooms = new();
            HashSet<string> executedScripts = new();
            foreach (var pair in manifest.Rooms)
            {
                var rPath = Path.Join(path, pair.Value);
                if (!File.Exists(rPath)) throw new Exception("Room file " + rPath + " doesn't exist");
                var rText = File.ReadAllText(rPath);
                result._rooms[pair.Key] = Room.FromJson(pair.Key, rText, result.LState, executedScripts, Directory.GetParent(rPath).FullName);
            }
            #endregion
            #region Starting Location
            result.PlayerX = manifest.Spawn.XLoc;
            result.PlayerY = manifest.Spawn.YLoc;
            result.CurrentRoom = result._rooms[manifest.Spawn.RoomName];
            #endregion
            return result;
        }

        private TiledGame(string name, string description)
        {
            Name = name;
            Description = description;

            #region Lua Methods
            var type = typeof(TiledGame);
            foreach (var method in type.GetMethods())
            {
                if (method.GetCustomAttribute(typeof(LuaCommand)) is object)
                {
                    LState[method.Name] = method.CreateDelegate(Expression.GetDelegateType(
                    (from parameter in method.GetParameters() select parameter.ParameterType)
                    .Concat(new[] { method.ReturnType })
                    .ToArray()), this);
                }
            }
            #endregion
        }

        public void SetWindowSize(int width, int height)
        {
            _windowHeight = height;
            _windowWidth = width;
            _wCenterX = width / 2;
            _wCenterY = height / 2;
        }

        public List<KeyValuePair<TileSlot?, int[]>> GetVisibleTiles() {
            List<KeyValuePair<TileSlot?, int[]>> result = new();
            int x = PlayerX;
            int y = PlayerY;
            var room = CurrentRoom;
            var layout = room.Layout;
            var width = layout[0].Length;
            var height = layout.Length;
            double vr = _visibleRange;

            for (int i = 0; i < RAYS.Length; ++i)
            {
                double r = RAYS[i];
                for (float n = 0; n < vr; n++)
                {
                    int newY = _wCenterY + (int)(Math.Sin(r) * n);
                    int newX = _wCenterX + (int)(Math.Cos(r) * n);
                    if (newY > _windowHeight || newX > _windowWidth) break;
                    int mi = newY - _wCenterY + y;
                    int mii = newX - _wCenterX + x;
                    TileSlot? tile = null;
                    var seethrough = true;
                    if (newY < 0 || newX < 0) continue;
                    if (mi >= 0 && mii >= 0 && mi < height && mii < width)
                    {
                        tile = layout[mi][mii];
                        seethrough = tile.Tile.Seethrough;
                    }
                    result.Add(new(tile, new int[] { newX, newY }));
                    if (!seethrough) break;
                }
            }
            return result;
        }

        public List<KeyValuePair<TileSlot, int[]>> GetAdjacentTiles(TileSelector ts)
        {
            var result = new List<KeyValuePair<TileSlot, int[]>>();
            for (int i = -1; i <= 1; i++)
            {
                for (int ii = -1; ii <= 1; ii++)
                {
                    if (i == 0 && ii == 0) continue;
                    var x = PlayerX + ii;
                    var y = PlayerY + i;
                    var t = CurrentRoom.Layout[y][x];
                    if (!ts(t)) continue;
                    result.Add(new(t, new int[] { ii, i }));
                }
            }
            return result;
        }

        public void Update(bool playerMoved)
        {
            #region Step Script
            if (playerMoved)
            {
                var l = CurrentRoom.Layout;
                var t = l[PlayerY][PlayerX].Tile;
                t.ExecuteScript(LState, TileEvents.Step);
            }
            #endregion
        }
        #region Lua Commands
        [LuaCommand]
        public bool SetTile(int x, int y, string tileName)
        {
            var room = CurrentRoom;
            var layout = room.Layout;
            if (x < 0 || y < 0 || x >= layout[0].Length || y >= layout.Length) return false;
            var tSet = room.Tileset;
            if (!tSet.ContainsKey(tileName)) return false;
            layout[y][x].Tile = tSet[tileName];
            return true;
        }
        #endregion
        #region Visibility Rays
        static readonly double[] RAYS = new double[200];

        static TiledGame()
        {
            var l = RAYS.Length;
            for (int i = 0; i < l; ++i)
                RAYS[i] = 2 * Math.PI * i / l;
        }
        #endregion
        #region Player

        public int PlayerX { get; set; }
        public int PlayerY { get; set; }
        private int _visibleRange = 10;

        public bool MovePlayer(int xDiff, int yDiff)
        {
            int newX = PlayerX + xDiff;
            int newY = PlayerY + yDiff;
            if (newX < 0 || newY < 0 || newX >= CurrentRoom.Layout[0].Length || newY >= CurrentRoom.Layout.Length) return false;
            var t = CurrentRoom.Layout[newY][newX];
            if (!t.Tile.Passable) return false;
            PlayerY = newY;
            PlayerX = newX;
            return true;
        }

        #endregion
        #region JSON
        class JManifest
        {
            [JsonProperty("name", Required = Required.Always)]
            public string Name { get; set; }
            [JsonProperty("description")]
            public string Description { get; set; }
            [JsonProperty("spawn", Required=Required.Always)]
            public JSpawn Spawn { get; set; }
            [JsonProperty("rooms", Required=Required.Always)]
            public Dictionary<string, string> Rooms { get; set; }

            public class JSpawn
            {
                [JsonProperty("room_name", Required = Required.Always)]
                public string RoomName { get; set; }
                [JsonProperty("x_loc", Required = Required.Always)]
                public int XLoc { get; set; }
                [JsonProperty("y_loc", Required = Required.Always)]
                public int YLoc { get; set; }
            }
        }
        #endregion
    }
}