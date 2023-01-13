using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Content;
using Microsoft.Xna.Framework.Graphics;
using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

class AssetsManager
{
    static private string MANIFEST_FILE = "manifest.json";
    private Dictionary<string, Dictionary<string, Texture2D>> _tiles;
    public Texture2D ErrorTex { get; }
    public Texture2D RedOutline { get; }
    public Texture2D PlayerBase { get; }

    public AssetsManager(string path, GraphicsDeviceManager graphics) {
        #region Manifest
        var mPath = Path.Combine(path, MANIFEST_FILE);
        if (!File.Exists(mPath)) throw new Exception(MANIFEST_FILE + " file not found in " + path);
        string mText = File.ReadAllText(mPath);
        var manifest = JsonConvert.DeserializeObject<JAssets>(mText);
        if (manifest is null) throw new Exception("Failed to parse " + MANIFEST_FILE + ": " + mText);
        #endregion
        #region Error Texture
        ErrorTex = LoadPNG(Path.Combine(path, manifest.ErrorTexPath), graphics);
        #endregion
        #region Tiles
        _tiles = new();
        foreach (var pair in manifest.Tiles)
        {
            var roomName = pair.Key;
            var tiles = pair.Value;
            Dictionary<string, Texture2D> tDict = new();
            foreach (var tPair in tiles)
            {
                var t = LoadPNG(Path.Combine(path, tPair.Value), graphics);
                tDict[tPair.Key] = t;
            }
            _tiles[roomName] = tDict;
        }
        #endregion
        #region Player
        PlayerBase = LoadPNG(Path.Combine(path, manifest.Player.BasePath), graphics);
        #endregion
        RedOutline = OutlineTex(graphics.GraphicsDevice, 64, 64, Color.Red, 2);
    }

    public Texture2D GetTile(string roomName, string tileName)
    {
        if (!_tiles.ContainsKey(roomName)) throw new Exception("No room with name " + roomName + " located in assets");
        var rDict = _tiles[roomName];
        if (!rDict.ContainsKey(tileName)) throw new Exception("No tile with name " + tileName + " located in assets (room: " + roomName + ")");
        return rDict[tileName];
    }

    public Texture2D OutlineTex(GraphicsDevice _graphics, int width, int height, Color color, int size=1)
    {
        Texture2D result = new(_graphics, width, height);
        Color[] data = new Color[height*width];
        for (int i = 0; i < height; i++)
        {
            for (int ii = 0; ii < width; ii++)
            {
                if (!(i < size || ii < size || i >= height - size || ii >= width - size)) continue;
                data[i * height + ii] = color;
            }
        }
        result.SetData(data);
        return result;
    }
    #region Utility
    private static Texture2D LoadPNG(string path, GraphicsDeviceManager graphics)
    {
        FileStream fs = new(path, FileMode.Open);
        var result = Texture2D.FromStream(graphics.GraphicsDevice, fs);
        fs.Close();
        return result;
    }
    #endregion
    #region JSON
    class JAssets
    {
        [JsonProperty("tiles", Required=Required.Always)]
        public Dictionary<string, Dictionary<string, string>> Tiles { get; set; }
        [JsonProperty("error", Required = Required.Always)]
        public string ErrorTexPath { get; set; }
        [JsonProperty("player", Required=Required.Always)]
        public JPlayer Player { get; set; }
    }

    class JPlayer
    {
        [JsonProperty("base", Required=Required.Always)]
        public string BasePath { get; set; }
    }
    #endregion
}
