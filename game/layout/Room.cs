using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using NLua;

namespace Tiled.Layout
{
    public class TileSlot
    {
        public Tile Tile { get; set; }
        public TileSlot(Tile tile)
        {
            Tile = tile;
        }
    }

    public class Room
    {
        public string Name { get; }
        public TileSlot[][] Layout { get; }
        public Dictionary<string, Tile> Tileset { get; }

        public Room(string name, TileSlot[][] layout, Dictionary<string, Tile> tileset)
        {
            Layout = layout;
            Name = name;
            Tileset = tileset;
        }

        public static Room FromJson(string roomName, string json, Lua lState, HashSet<string> executedScripts, string path)
        {
            JRoom? result = JsonConvert.DeserializeObject<JRoom>(json);
            if (result is null) throw new Exception("Failed to parse room: " + json);
            return result.Get(roomName, lState, executedScripts, path);
        }

        class JRoom
        {
            [JsonProperty("tileset", Required = Required.Always)]
            public Dictionary<char, Tile.JTile> Tileset { get; set; }

            [JsonProperty("layout", Required = Required.Always)]
            public string Layout { get; set; }

            public Room Get(string roomName, Lua lState, HashSet<string> executedScripts, string path)
            {
                var lines = Layout.Split("\n");
                TileSlot[][] layout = new TileSlot[lines.Length][];

                for (int i = 0; i < lines.Length; i++)
                {
                    layout[i] = new TileSlot[lines[i].Length];
                    for (int ii = 0; ii < lines[i].Length; ii++)
                    {
                        layout[i][ii] = new(Tileset[lines[i][ii]].Get(lState, executedScripts, path));
                    }
                }
                var tSet = new Dictionary<string, Tile>();
                foreach (var tile in Tileset.Values)
                {
                    tSet[tile.Name] = tile.Get(lState, executedScripts, path);
                }
                var result = new Room(roomName, layout, tSet);

                return result;
            }
        }
    }
}
