using Newtonsoft.Json;
using NLua;

namespace Tiled.Layout
{
    public enum TileEvents
    {
        Interact,
        Step
    }

    public class Tile
    {
        public string Name { get; }
        public string DisplayName { get; }
        public bool Passable { get; }
        public bool Seethrough { get; }
        public Dictionary<TileEvents, string>? Events { get; set; }


        public string GetEvent(TileEvents e)
        {
            if (Events is null) return "";
            if (!Events.ContainsKey(e)) return "";
            return Events[e];
        }

        private Tile(JTile j, Lua lState, HashSet<string> executedScripts, string path)
        {
            Name = j.Name;
            DisplayName = j.DisplayName;
            Passable = j.Passable;
            Seethrough = j.Seethrough;

            if (j.Events is null) return;
            if (!j.Events.ContainsKey("script")) throw new Exception("Events of " + Name + " doesn't contain script path");
            var sPath = j.Events["script"];
            if (!executedScripts.Contains(sPath))
            {
                lState.DoFile(Path.Combine(path, sPath));
                executedScripts.Add(sPath);
            }
            Events = new Dictionary<TileEvents, string>();
            foreach (var pair in j.Events)
            {
                if (pair.Key == "script") continue;
                TileEvents eKey;
                Enum.TryParse(char.ToUpper(pair.Key[0]) + pair.Key.Substring(1), out eKey);
                Events[eKey] = pair.Value;
            }
        }

        public void ExecuteScript(Lua lState, TileEvents e)
        {
            if (Events is null) return;
            if (!Events.ContainsKey(e)) return;
            var f = lState[Events[e]] as LuaFunction;
            if (f == null) throw new Exception(Events[e] + " function was not declared");
            f.Call();
        }


        public class JTile
        {
            [JsonProperty("name", Required = Required.Always)]
            public string Name { get; set; } = "no-name";
            [JsonProperty("display_name", Required = Required.Always)]
            public string DisplayName { get; set; } = "no-dname";
            [JsonProperty("passable", Required = Required.Always)]
            public bool Passable { get; set; } = false;
            [JsonProperty("seethrough", Required = Required.Always)]
            public bool Seethrough { get; set; } = true;
            [JsonProperty("events")]
            public Dictionary<string, string>? Events { get; set; }

            public Tile Get(Lua lState, HashSet<string> executedScripts, string path)
            {
                return new Tile(this, lState, executedScripts, path);
            }
        }
    }
}