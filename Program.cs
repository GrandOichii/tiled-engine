using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;
using Microsoft.Xna.Framework.Input;
using System;
using Tiled;
using Tiled.Layout;

public delegate void GAction(GameTime gameTime);

class MGWrapper : Game
{
    #region Game
    private TiledGame _game;
    private int _tileHeight = 64;
    private int _tileWidth = 64;
    private int _tileCountX;
    private int _tileCountY;

    #endregion
    #region Graphics
    private GraphicsDeviceManager _graphics;
    private SpriteBatch _spriteBatch;
    private AssetsManager _assets;
    private string _assetsPath;
    #endregion

    private State _currentState;

    public MGWrapper(int wWidth, int wHeight, string gamePath, string assetsPath)
    {
        _graphics = new GraphicsDeviceManager(this);
        _graphics.PreferredBackBufferWidth = wWidth;
        _graphics.PreferredBackBufferHeight = wHeight;
        CorrectTileCounts(wWidth, wHeight);
        //_graphics.IsFullScreen = true;
        _graphics.ApplyChanges();


        IsMouseVisible = true;

        _game = TiledGame.Load(gamePath);
        _game.SetWindowSize(_tileCountX, _tileCountY);
        Window.Title = _game.Name;
        _assetsPath = assetsPath;

        #region State Creation
        var mState = new MovementState(this);
        var iState = new InteractState(this, mState);
        mState.IState = iState;

        _currentState = mState;
        #endregion
    }

    private void CorrectTileCounts(int wWidth, int wHeight)
    {
        _tileCountX = wWidth / _tileWidth;
        _tileCountY = wHeight / _tileHeight;
    }

    protected override void Initialize()
    {
        base.Initialize();

        //Window.Title
    }

    protected override void LoadContent()
    {
        _spriteBatch = new(_graphics.GraphicsDevice);
        _assets = new(_assetsPath, _graphics);
        base.LoadContent();
    }

    #region Key Locking
    private Dictionary<Keys, bool> _keyLocks = new();

    public void Lock(Keys key)
    {
        _keyLocks[key] = false;
    }

    public bool IsUnlocked(Keys key) => !_keyLocks.ContainsKey(key) || _keyLocks[key];

    public void CheckUnlockKeys()
    {
        var kState = Keyboard.GetState();
        foreach (var key in _keyLocks.Keys)
        {
            if (kState.IsKeyDown(key)) continue;
            _keyLocks[key] = true;
        }
    }
    #endregion

    protected override void Update(GameTime gameTime)
    {
        _currentState.Update(gameTime);
        CheckUnlockKeys();
        base.Update(gameTime);
    }

    protected override void Draw(GameTime gameTime)
    {
        base.Draw(gameTime);
        _graphics.GraphicsDevice.Clear(Color.Black);
        _spriteBatch.Begin();
        _currentState.Draw(gameTime);
        _spriteBatch.End();
    }

    #region States
    abstract class State
    {
        protected MGWrapper _parent;
        protected State? _parentState;
        public State(MGWrapper parent, State? parentState=null)
        {
            _parent = parent;
            _parentState = parentState;
        }

        public virtual void Update(GameTime gameTime)
        {
            if (_parentState is null) return;
            _parentState.Update(gameTime);
        }

        public virtual void Draw(GameTime gameTime)
        {
            if (_parentState is null) return;
            _parentState.Draw(gameTime);
        }
    }

    abstract class KeyboardInState : State
    {
        static protected Dictionary<Keys[], int[]> DIRECTIONAL_COORDS = new()
        {
            { new Keys[]{ Keys.NumPad7, Keys.Y}, new int[2]{-1, -1} },
            { new Keys[] {Keys.NumPad3, Keys.N }, new int[2]{1, 1} },
            { new Keys[] {Keys.NumPad9, Keys.U }, new int[2]{1, -1} },
            { new Keys[] {Keys.NumPad1, Keys.B }, new int[2]{-1, 1} },
            { new Keys[] {Keys.NumPad2, Keys.S }, new int[2]{0, 1} },
            { new Keys[] {Keys.NumPad8, Keys.W }, new int[2]{0, -1} },
            { new Keys[] {Keys.NumPad4, Keys.A }, new int[2]{-1, 0} },
            { new Keys[] {Keys.NumPad6, Keys.D }, new int[2]{1, 0} },
        };

        protected KeyboardInState(MGWrapper parent, State? parentState=null) : base(parent, parentState)
        {
        }

        public Dictionary<Keys, GAction> KeyboardActions { get; } = new();

        protected void CheckKeys(GameTime gt)
        {
            var kState = Keyboard.GetState();
            foreach (var pair in KeyboardActions)
            {
                var kKey = pair.Key;
                if (kState.IsKeyDown(kKey) && _parent.IsUnlocked(kKey))
                {
                    pair.Value(gt);
                    _parent.Lock(kKey);
                }
            }
        }
    }

    class MovementState : KeyboardInState
    {
        private bool _playerMoved = false;
        public InteractState IState { get; set; }

        public MovementState(MGWrapper parent, State? parentState=null) : base(parent, parentState)
        {
            // exiting the game
            KeyboardActions.Add(Keys.Escape, (GameTime gt) => _parent.Exit());
            
            // movement keys
            foreach (var pair in DIRECTIONAL_COORDS)
            {
                var diff = pair.Value;
                GAction action = delegate (GameTime gt)
                {
                    if (_parent._game.MovePlayer(diff[0], diff[1]))
                        _playerMoved = true;
                };
                foreach (var key in pair.Key)
                {
                    KeyboardActions.Add(key, action);
                }
            }

            // interact keys
            KeyboardActions.Add(Keys.E, (GameTime gt) =>
            {
                var tiles = _parent._game.GetAdjacentTiles((TileSlot t) => t.Tile.GetEvent(TileEvents.Interact).Length != 0);
                if (tiles.Count == 0)
                {
                    // TODO: notify player that there are no interactable tiles nearby
                    return;
                }
                IState.Tiles = tiles;
                _parent._currentState = IState;
            });
        }

        public override void Draw(GameTime gameTime)
        {
            var rName = _parent._game.CurrentRoom.Name;
            var pairs = _parent._game.GetVisibleTiles();
            foreach (var pair in pairs)
            {
                var tile = pair.Key;
                if (tile is null) continue;
                var coords = pair.Value;
                var t = _parent._assets.GetTile(rName, tile.Tile.Name);
                _parent._spriteBatch.Draw(t, new Rectangle(
                    coords[0] * _parent._tileWidth,
                    coords[1] * _parent._tileHeight,
                    _parent._tileWidth,
                    _parent._tileHeight
                ), Color.White);
            }
            var v2 = new Vector2((_parent._graphics.PreferredBackBufferWidth - _parent._tileWidth) / 2, (_parent._graphics.PreferredBackBufferHeight - _parent._tileHeight) / 2);
            var rec = new Rectangle(
                (_parent._graphics.PreferredBackBufferWidth - _parent._tileWidth) / 2,
                (_parent._graphics.PreferredBackBufferHeight - _parent._tileHeight) / 2,
                _parent._tileWidth,
                _parent._tileHeight
            );

            _parent._spriteBatch.Draw(_parent._assets.PlayerBase, rec, null, Color.White, 0, Vector2.Zero, SpriteEffects.FlipHorizontally, 0);
            #region Outline Mask
            //for (int i = 0; i < _parent._tileCountY; i++)
            //{
            //    for (int ii = 0; ii < _parent._tileCountX; ii++)
            //    {
            //        _parent._spriteBatch.Draw(_parent._assets.RedOutline, new Rectangle(
            //            ii * _parent._tileWidth,
            //            i * _parent._tileHeight,
            //            _parent._tileWidth,
            //            _parent._tileHeight
            //        ), Color.White);
            //    }
            #endregion
        }

        public override void Update(GameTime gameTime)
        {
            _playerMoved = false;
            base.Update(gameTime);
            CheckKeys(gameTime);
            _parent._game.Update(_playerMoved);
        }
    }

    class InteractState : KeyboardInState
    {
        public List<KeyValuePair<TileSlot, int[]>> Tiles { get; set; }

        public InteractState(MGWrapper parent, State? parentState = null) : base(parent, parentState)
        {
            GAction quit = (GameTime gt) => _parent._currentState = parentState;
            KeyboardActions.Add(Keys.Space, quit);
            KeyboardActions.Add(Keys.Escape, quit);

            foreach (var pair in DIRECTIONAL_COORDS)
            {
                var diff = pair.Value;
                GAction action = delegate (GameTime gt)
                {
                    foreach (var tile in Tiles)
                    {
                        if (tile.Value[0] != diff[0] || tile.Value[1] != diff[1]) continue;
                        var game = _parent._game;
                        game.CurrentRoom.Layout[game.PlayerY + diff[1]][game.PlayerX + diff[0]].Tile.ExecuteScript(parent._game.LState, TileEvents.Interact);
                        break;
                    }
                    quit(gt);
                };
                foreach (var key in pair.Key)
                {
                    KeyboardActions.Add(key, action);
                }
            }

        }

        public override void Draw(GameTime gameTime)
        {
            base.Draw(gameTime);
            var cX = (_parent._graphics.PreferredBackBufferWidth - _parent._tileWidth) / 2;
            var cY = (_parent._graphics.PreferredBackBufferHeight - _parent._tileHeight) / 2;
            foreach (var tile in Tiles) {
                _parent._spriteBatch.Draw(_parent._assets.RedOutline, 
                    new Rectangle(
                        cX + _parent._tileWidth * tile.Value[0],
                        cY + _parent._tileHeight * tile.Value[1],
                        _parent._tileWidth,
                        _parent._tileHeight
                    ), Color.White);
            }
        }

        public override void Update(GameTime gameTime)
        {
            CheckKeys(gameTime);
        }
    }
    #endregion
}

class Program {
    public static void Main() {
        Console.WriteLine("Project start");
        var g = new MGWrapper(64 * 21, 64 * 13, "C:\\Users\\ihawk\\Documents\\code\\tiled\\creator\\Project1", "C:\\Users\\ihawk\\Documents\\code\\tiled\\assets");
        g.Run();
    }
}