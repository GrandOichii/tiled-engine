# add regex filtering of room names and project name

import os
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from luaparser import ast, astnodes, builder

from PyQt5.Qsci import QsciScintilla, QsciLexerLua

from game import Game, Room, Tile


TILE_HW = 32
BASE_COLOR = QColor('gray')
SELECTED_COLOR = QColor('red')
MIN_TILES_X = 21
MIN_TILES_Y = 21

class ScriptWidget(QsciScintilla):
    def __init__(self, parent) -> None:
        super().__init__(parent)

        lexer = QsciLexerLua()
        self.setLexer(lexer)
        self.setAutoIndent(True)
        # self.setAutoCompletionSource()
        
        self.setMinimumSize(600, 450)

class ScriptEditor(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowTitle('Tile script editing')
        self.saved = False
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()

        buttons_layout = QHBoxLayout()

        self.script_edit = ScriptWidget(self)
        self.script_edit.setMinimumSize(400, 600)
        font = QFont()
        font.setPointSize(18)
        self.script_edit.setFont(font)
        main_layout.addWidget(self.script_edit)

        save_button = QPushButton('Save')
        save_button.clicked.connect(self.save_action)
        buttons_layout.addWidget(save_button)
        
        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(self.cancel_action)
        buttons_layout.addWidget(cancel_button)

        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

    def get_result(self) -> str:
        return self.script_edit.text()

    def load(self, text: str):
        self.script_edit.setText(text)

    def unload(self):
        self.script_edit.setText('')
    
    # actions
    def save_action(self):
        try:
            text = self.script_edit.text()
            ast.parse(text)
        except builder.SyntaxException as e:
            QMessageBox.critical(self, 'Lua parcing error', f'Parsing error:\n\n{str(e)}')
            return
        self.saved = True

        self.close()

    def cancel_action(self):
        self.saved = False
        self.close()

class RoomLI(QListWidgetItem):
    def __init__(self, name: str):
        QListWidgetItem.__init__(self)
        self.label = QLabel(name)
        self.room = Room()
        self.room.layout = []
        for i in range(MIN_TILES_Y):
            row = []
            for j in range(MIN_TILES_X):
                row += [None]
            self.room.layout += [row]

        self.room.name = lambda: name

class TileLI(QListWidgetItem):
    def __init__(self, tile: Tile):
        QListWidgetItem.__init__(self)
        self.wid: QWidget = QWidget()
        layout = QVBoxLayout()
        self.im = QLabel()
        self.im.setPixmap(tile.image)
        layout.addWidget(self.im)
        layout.addWidget(QLabel(tile.name))
        self.wid.setLayout(layout)
        self.setSizeHint(self.wid.sizeHint())
        self.tile = tile

class RoomList(QListWidget):
    def __init__(self, parent) -> None:
        super().__init__(None)
        self.parent_te = parent

class TileWidget(QLabel):
    def __init__(self, parent, tile=None) -> None:
        super().__init__()
        self.selected = False
        self.x_pos = -1
        self.y_pos = -1
        self.parent_ = parent
        self.tile = tile
        self.setMinimumSize(TILE_HW, TILE_HW)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if self.tile is None: return
        self.setPixmap(self.tile.image)

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        self.parent_.set_focus(self)
        return super().mousePressEvent(ev)

    def set_selected(self, value: bool):
        self.selected = value
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        hw = TILE_HW
        painter = QPainter(self)
        # brush = QBrush(self.color)
        # painter.setBrush(brush)        
        # painter.drawRect(0, 0, hw, hw)
        s = 0

        pen = QPen(BASE_COLOR)
        painter.setPen(pen)
        painter.drawRect(s, s, hw - s*2, hw - s*2)
        if self.selected:
            ss = 1
            pen = QPen(SELECTED_COLOR)
            painter.setPen(pen)
            painter.drawRect(ss, ss, hw - ss*2, hw - ss*2)
        # if self.highlighted:
        #     brush.setColor(TILE_HIGHLIGHT_COLOR)
        #     brush.setStyle(Qt.BrushStyle.DiagCrossPattern)
        #     painter.setBrush(brush)
        #     painter.drawRect(2, 2, hw-4, hw-4)
        # painter.drawPoint(hw // 2, hw // 2)

    def sizeHint(self) -> QSize:
        return QSize(TILE_HW, TILE_HW)

    def set_size(hw):
        global TILE_HW

class TilesLayout(QScrollArea):
    def __init__(self, parent: 'Creator') -> None:
        super().__init__()
        self.x_count = MIN_TILES_X
        self.y_count = MIN_TILES_Y
        self.parent_ = parent

        wid = QWidget()
        self.tiles_layout = QGridLayout()
        self.tiles_layout.setSpacing(0)
        # p = QPixmap('error.png')
        # s = p.size()
        # TileWidget.set_size(s.width())
        # work on adding tiles
        for i in range(self.y_count):
            for j in range(self.x_count):
                l = TileWidget(self.parent_)
                l.y_pos = j
                l.x_pos = i
                # l.setPixmap(p)
                self.tiles_layout.addWidget(l, i, j)
        wid.setLayout(self.tiles_layout)
        self.setWidgetResizable(True)
        self.setMinimumSize(600, 300)
        self.setWidget(wid)
    
class TileEditor(QDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.initUI()
        self.parent_ = parent
        self.saved = False
        self.image = None
        self.image_path = None

        self.last = None

        self.script_editor = ScriptEditor(self)
        self.script_result: str = ''

    def initUI(self):
        mainLayout = QVBoxLayout()
        form = QFormLayout()
        self.name_field = QLineEdit()
        form.addRow(QLabel('Name:'), self.name_field)
        self.display_name_field = QLineEdit()
        form.addRow(QLabel('Display name:'), self.display_name_field)
        self.passable_field = QCheckBox()
        form.addRow(QLabel('Passable:'), self.passable_field)
        self.seethrough_field = QCheckBox()
        form.addRow(QLabel('Seethrough:'), self.seethrough_field)
        self.image_button = QPushButton('Image')
        self.image_button.clicked.connect(self.set_image_button)
        form.addRow(QLabel('Image:'), self.image_button)

        edit_script_button = QPushButton('Edit script')
        edit_script_button.clicked.connect(self.edit_script_action)
        form.addWidget(edit_script_button)
        self.step_script_box = QComboBox()
        form.addRow(QLabel('Step script'), self.step_script_box)
        self.interact_script_box = QComboBox()
        form.addRow(QLabel('Interact script'), self.interact_script_box)

        mainLayout.addLayout(form)

        buttons_layout = QHBoxLayout()
        save_button = QPushButton('Save')
        save_button.clicked.connect(self.save_action)
        buttons_layout.addWidget(save_button)

        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(self.cancel_action)
        mainLayout.addLayout(buttons_layout)
        buttons_layout.addWidget(cancel_button)
        self.setLayout(mainLayout)

    def set_image_button(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', filter="Image files (*.jpg *.png)")
        imagePath = fname[0]
        if imagePath == '': return
        self.image_path = imagePath
        self.image = QPixmap(imagePath)
        self.image_button.setText('')
        self.image_button.setIcon(QIcon(self.image))
        self.image_button.setIconSize(self.image.rect().size())

    def load(self, tile: Tile):
        self.setWindowTitle(tile.name)
        self.saved = False
        self.image_button.setText('')
        self.name_field.setText(tile.name)
        self.display_name_field.setText(tile.display_name)
        self.passable_field.setChecked(tile.passable)
        self.seethrough_field.setChecked(tile.seethrough)
        self.script_editor.load(tile.script)
        self.script_result = tile.script
        self.add_funcs()
        self.step_script_box.setCurrentText(tile.step_func)
        self.interact_script_box.setCurrentText(tile.interact_func)
        self.last = tile

    def add_funcs(self):
        f_names = ['']
        sls = self.step_script_box.currentText()
        ils = self.interact_script_box.currentText()
        self.step_script_box.clear()
        self.interact_script_box.clear()
        tree = ast.parse(self.script_result)
        for node in ast.walk(tree):
            if isinstance(node, astnodes.Function):
                f_names += [node.name.id]
        self.step_script_box.addItems(f_names)
        if sls in f_names:
            self.step_script_box.setCurrentText(sls)
        self.interact_script_box.addItems(f_names)        
        if ils in f_names:
            self.interact_script_box.setCurrentText(ils)

    def unload(self):
        self.setWindowTitle('New tile')
        self.name_field.setText('')
        self.display_name_field.setText('')
        self.passable_field.setChecked(False)
        self.seethrough_field.setChecked(False)
        self.image_button.setIcon(QIcon())
        self.image_button.setText('Image')
        self.step_script_box.clear()
        self.interact_script_box.clear()
        self.image_path = None
        self.image = None
        self.script_editor.unload()
        self.name_field.setFocus()
        self.saved = False
        self.last = None

    def pack(self) -> Tile:
        result = Tile()
        result.name = self.name_field.text()
        result.display_name = self.display_name_field.text()
        result.passable = self.passable_field.isChecked()
        result.seethrough = self.seethrough_field.isChecked()
        result.image = self.image
        result.image_path = self.image_path
        result.script = self.script_result
        result.step_func = self.step_script_box.currentText()
        result.interact_func = self.interact_script_box.currentText()
        return result

    def show_err(self, message: str):
        print(f'ERR: {message}')

    # actions
    def save_action(self):
        name = self.name_field.text()
        if name == '':
            self.show_err('Enter tile name')
            return
        
        if self.display_name_field.text() == '':
            self.show_err('Enter tile display name')
            return

        if self.image == None:
            self.show_err('Image not set')
            return

        if self.image_path == None:
            self.show_err('Image path not set')
            return

        if not self.parent_.can_add_tile(name) and not (self.last != None and self.last.name == name):
            self.show_err(f'Tile with name {name} already exists in {self.parent_.current_room.room.name()}')
            return
            
        # check if tile with name already exists
        self.saved = True
        self.close()

    def cancel_action(self):
        self.saved = False
        self.close()

    def edit_script_action(self):
        self.script_editor.exec_()
        if not self.script_editor.saved: return
        self.script_result = self.script_editor.get_result()
        self.add_funcs()

class Creator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.game: Game = None
        self.last_save_path: str = None
        self.saved = True
        self.watch_changes_list: list[QLineEdit|QTextEdit] = []
        self.current_room: RoomLI = None
        self.tile_editor = TileEditor(self)

        self.first_selected_tile = None
        self.second_selected_tile = None

        self.initUI()

    def initUI(self): 
        self.tabs = QTabWidget()

        mainLayout = QHBoxLayout()

        # menu bar actions
        self.menu_new_action = QAction('&New', self)
        self.menu_new_action.setShortcut('Ctrl+Shift+N')
        self.menu_new_action.setStatusTip('Create new project')
        self.menu_new_action.triggered.connect(self.new_action)

        self.menu_load_action = QAction('&Load', self)
        self.menu_load_action.setShortcut('Ctrl+O')
        self.menu_load_action.setStatusTip('Load existing project')
        self.menu_load_action.triggered.connect(self.load_action)

        self.menu_save_action = QAction('&Save', self)
        self.menu_save_action.setShortcut('Ctrl+S')
        self.menu_save_action.setStatusTip('Save')
        self.menu_save_action.triggered.connect(self.save_action)

        self.menu_save_as_action = QAction('&Save as', self)
        self.menu_save_as_action.setShortcut('Ctrl+Shift+S')
        self.menu_save_as_action.setStatusTip('Save as')
        self.menu_save_as_action.triggered.connect(self.save_as_action)

        self.menu_quit_action = QAction('&Quit', self)
        self.menu_quit_action.setShortcut('Ctrl+Q')
        self.menu_quit_action.setStatusTip('Quit')
        self.menu_quit_action.triggered.connect(self.close)

        self.menu_new_room_action = QAction('&New room', self)
        self.menu_new_room_action.setShortcut('Ctrl+N')
        self.menu_new_room_action.setStatusTip('Create new room')
        self.menu_new_room_action.triggered.connect(self.new_room_action)

        self.menu_new_tile_action = QAction('&New tile', self)
        self.menu_new_tile_action.setShortcut('Ctrl+T')
        self.menu_new_tile_action.setStatusTip('Create new tile')
        self.menu_new_tile_action.triggered.connect(self.new_tile_action)

        menu_bar = self.menuBar()
        self.file_menu = menu_bar.addMenu('&File')
        self.file_menu.addAction(self.menu_new_action)
        self.file_menu.addAction(self.menu_load_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.menu_save_action)
        self.file_menu.addAction(self.menu_save_as_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.menu_quit_action)

        self.room_menu = menu_bar.addMenu('&Rooms')
        self.room_menu.addAction(self.menu_new_room_action)
        self.file_menu.addSeparator()
        self.room_menu.addAction(self.menu_new_tile_action)

        # game info editing
        self.game_info_layout = QFormLayout()
        self.game_project_name_edit = QLineEdit()
        self.watch_changes_list += [self.game_project_name_edit]
        self.game_info_layout.addRow(QLabel('Project name'), self.game_project_name_edit)
        self.game_name_edit = QLineEdit()
        self.watch_changes_list += [self.game_name_edit]
        self.game_info_layout.addRow(QLabel('Name'), self.game_name_edit)
        self.game_rooms_list = QComboBox()
        self.game_rooms_list.activated.connect(self.chosen_spawn_room_action)
        self.game_info_layout.addRow(QLabel('Starting room: '), self.game_rooms_list)
        self.spawn_x_edit = QLineEdit()
        self.spawn_x_edit.setValidator(QIntValidator())
        self.watch_changes_list += [self.spawn_x_edit]
        self.game_info_layout.addRow(QLabel('Starting X location: '), self.spawn_x_edit)
        self.spawn_y_edit = QLineEdit()
        self.spawn_y_edit.setValidator(QIntValidator())
        self.watch_changes_list += [self.spawn_y_edit]
        self.game_info_layout.addRow(QLabel('Starting Y location: '), self.spawn_y_edit)
        self.game_info_layout.addWidget(QLabel('Description'))
        self.game_description_edit = QTextEdit()
        self.watch_changes_list += [self.game_description_edit]
        self.game_info_layout.addWidget(self.game_description_edit)

        # rooms
        rooms_sidebar_layout = QVBoxLayout()
        self.rooms_listw = RoomList(self)
        self.rooms_listw.itemClicked.connect(self.room_clicked_action)

        self.new_room_button = QPushButton('New room')
        self.new_room_button.clicked.connect(self.new_room_action)

        self.delete_room_button = QPushButton('Delete room')
        self.delete_room_button.clicked.connect(self.delete_room_action)

        rooms_sidebar_layout.addWidget(self.rooms_listw)
        rooms_sidebar_layout.addWidget(self.new_room_button)
        rooms_sidebar_layout.addWidget(self.delete_room_button)

        room_space_layout = QHBoxLayout()

        # main layout
        r_layout = QVBoxLayout()

        # tiles
        self.tiles_list = QListWidget()
        self.tiles_list.setWrapping(False)
        self.tiles_list.setFlow(QListWidget.LeftToRight)
        self.tiles_list.setMaximumHeight(100)
        self.tiles_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        buttons_layout = QHBoxLayout()
        
        new_tile_button = QPushButton('New tile')
        new_tile_button.clicked.connect(self.new_tile_action)

        edit_tile_button = QPushButton('Edit tile')
        edit_tile_button.clicked.connect(self.edit_tile_action)

        delete_tile_button = QPushButton('Delete tile')

        buttons_layout.addWidget(new_tile_button)
        buttons_layout.addWidget(edit_tile_button)
        buttons_layout.addWidget(delete_tile_button)

        tiles_grid = QGridLayout()

        self.tiles_layout = TilesLayout(self)
        class VertButton(QPushButton):
            def __init__(self, text: str):
                QPushButton.__init__(self, text)
                self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            def sizeHint(self) -> QSize:
                return super().sizeHint().transposed()

            def paintEvent(self, event: QPaintEvent) -> None:
                painter = QStylePainter(self)
                option = QStyleOptionButton()
                self.initStyleOption(option)
                painter.rotate(90)
                painter.translate(0, -1*self.width())
                option.rect = option.rect.transposed()
                painter.drawControl(QStyle.CE_PushButton, option)

        tiles_grid.addWidget(VertButton ('-'), 2, 0)
        tiles_grid.addWidget(VertButton('+'), 2, 1)
        tiles_grid.addWidget(VertButton('+'), 2, 3)
        tiles_grid.addWidget(VertButton('-'), 2, 4)
        tiles_grid.addWidget(QPushButton('-'), 0, 2)
        tiles_grid.addWidget(QPushButton('+'), 1, 2)
        tiles_grid.addWidget(QPushButton('+'), 3, 2)
        tiles_grid.addWidget(QPushButton('-'), 4, 2)
        tiles_grid.addWidget(self.tiles_layout, 2, 2)

        r_layout.addWidget(self.tiles_list)
        # r_layout.addWidget(scroll)
        r_layout.addLayout(buttons_layout)
        sr = QHBoxLayout()
        # sr.addStretch(1)
        sr.addLayout(tiles_grid, 1)
        sr.addStretch(1)
        r_layout.addLayout(sr)
        self.r_widget = QWidget()
        self.r_widget.setLayout(r_layout)
        self.r_widget.setEnabled(False)
        room_space_layout.addWidget(self.r_widget, 4)
        room_space_layout.addLayout(rooms_sidebar_layout, 1)
        mainLayout.addWidget(self.tabs)

        # watch for editing
        for w in self.watch_changes_list:
            w.textChanged.connect(self.invalidate_saved)

        # adding tabs
        self.game_info_tab = QWidget()
        self.game_info_tab.setLayout(self.game_info_layout)
        self.tabs.addTab(self.game_info_tab, 'Game info')

        self.room_info_tab = QWidget()
        self.room_info_tab.setLayout(room_space_layout)
        self.tabs.addTab(self.room_info_tab, 'Rooms')

        wid = QWidget(self)
        self.setCentralWidget(wid)
        wid.setLayout(mainLayout)

        self.set_enabled_game_specific(False)
        self.setMinimumSize(QSize(800, 600))
        self.setWindowTitle('Tiled Creator')

    def mb(self, text: str):
        m = QMessageBox(self)
        m.setWindowTitle(self.game.name())
        m.setText(text)
        m.exec_()
        # return QMessageBox.warning(self, self.game.name(), text)

    def set_enabled_game_specific(self, v):
        self.menu_save_action.setEnabled(v)
        self.menu_save_as_action.setEnabled(v)
        self.room_menu.setEnabled(v)
        self.game_info_layout.setEnabled(v)
        self.game_name_edit.setEnabled(v)
        self.game_description_edit.setEnabled(v)
        self.game_project_name_edit.setEnabled(v)
        self.new_room_button.setEnabled(v)
        self.delete_room_button.setEnabled(v)
        self.game_rooms_list.setEnabled(v)
        self.tabs.setEnabled(v)

    def get_selected_tiles(self) -> list[TileWidget]:
        result = []
        if self.first_selected_tile is None: return result
        x1 = self.first_selected_tile.x_pos
        y1 = self.first_selected_tile.y_pos
        x2 = x1
        y2 = y1
        if self.second_selected_tile is not None:
            x2 = self.second_selected_tile.x_pos
            y2 = self.second_selected_tile.y_pos
        if x1 > x2:
            t = x1
            x1 = x2
            x2 = t
        if y1 > y2:
            t = y1
            y1 = y2
            y2 = t
        for i in range(y1, y2 + 1):
            for j in range(x1, x2 + 1):
                result += [self.tiles_layout.tiles_layout.itemAtPosition(i, j).widget()]
        return result

    def set_selected_tiles(self, value: bool):
        tiles = self.get_selected_tiles()
        for t in tiles:
            t.set_selected(value)

    def unselect_tiles(self):
        self.set_selected_tiles(False)

    def select_tiles(self):
        self.set_selected_tiles(True)

    def set_focus(self, t: TileWidget):
        self.unselect_tiles()
        tt = self.tiles_layout.tiles_layout.itemAtPosition(t.y_pos, t.x_pos).widget()
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:
            self.second_selected_tile = tt
        else:
            self.second_selected_tile = None
            self.first_selected_tile = tt
        self.select_tiles()

    def can_add_tile(self, tile_name):
        for t in self.current_room.room.tileset:
            if t.name == tile_name:
                return False
        return True

    def update_rooms_list(self):
        self.game_rooms_list.clear()
        for r in self.game.rooms:
            self.game_rooms_list.addItem(r.name())

    def save(self):
        err = self.game.save(self.last_save_path)
        if err is None:
            self.validate_saved()
            return
        print(err)

    def invalidate_saved(self):
        self.saved = False
        self.setWindowTitle(self.game.project_name() + '*')

    def validate_saved(self):
        self.saved = True
        self.setWindowTitle(self.game.project_name())

    def yn(self, title: str, message: str) -> bool:
        return QMessageBox.question(self, title, message, QMessageBox.Yes|QMessageBox.No, QMessageBox.No) == QMessageBox.Yes

    def add_tile_to_list(self, tile: Tile):
        item = TileLI(tile)
        # item = QListWidgetItem()
        self.tiles_list.addItem(item)
        self.tiles_list.setItemWidget(item, item.wid)
        # self.tiles_list.setItemWidget(item, QLabel('aaa'))

    def load_from_game(self):
        game = self.game
        self.bind_values()

        self.game_name_edit.setText(game.temp_name)
        del game.temp_name

        self.game_description_edit.setText(game.temp_description)
        del game.temp_description

        self.game_project_name_edit.setText(game.temp_project_name)
        del game.temp_project_name

        self.spawn_x_edit.setText(str(game.spawn_temp_x_loc))
        del game.spawn_temp_x_loc

        self.spawn_y_edit.setText(str(game.spawn_temp_y_loc))
        del game.spawn_temp_y_loc

        # rooms
        for room in self.game.rooms:
            self.r_widget.setEnabled(True)
            n = room.temp_name
            del room.temp_name
            r = RoomLI(n)
            room.name = lambda: n
            r.room = room
            self.rooms_listw.addItem(r)
            self.rooms_listw.setItemWidget(r, r.label)

            for tile in room.tileset:
                tile.image = QPixmap(tile.image_path)

        self.update_rooms_list()

        # self.update_room_panel()
        self.game_rooms_list.setCurrentText(self.game.spawn_room.name())

        self.set_enabled_game_specific(True)

    def bind_values(self):
        self.game.project_name = self.game_project_name_edit.text
        self.game.name = self.game_name_edit.text
        self.game.description = self.game_description_edit.toPlainText
        self.game.spawn_x_loc = lambda: int(self.spawn_x_edit.text() if self.spawn_x_edit.text() else -1)
        self.game.spawn_y_loc = lambda: int(self.spawn_y_edit.text() if self.spawn_x_edit.text() else -1)

    # actions
    def new_action(self):
        if not self.saved and self.yn('New Game', 'Are you sure you want to create a new game? Unsaved changes will be discarded.'):
            return
            
        self.game = Game()
        self.bind_values()
        self.set_enabled_game_specific(True)

        self.game_project_name_edit.setText('Project1')
        self.game_name_edit.setText('Game1')
        self.game_description_edit.setText('This is the description of your game.\n\nAuthor: ' + os.getlogin())
        self.invalidate_saved()

    def load_action(self):
        dir = QFileDialog.getExistingDirectory(self, "Select Directory")
        # try:
        self.game = Game.load(dir)
        self.load_from_game()
        # except Exception as e:
        #     QMessageBox.critical(self, 'Loading project', f'Failed to load project:\n\n{str(e)}')

    def save_action(self):
        if self.game is None:
            return
        if self.last_save_path is None or not os.path.exists(self.last_save_path):
            self.save_as_action()
            return
        self.save()

    def save_as_action(self):
        if self.game is None:
            return
        dir = QFileDialog.getExistingDirectory(self, "Select Directory")
        if dir == '': return
        self.last_save_path = os.path.join(str(dir), self.game.project_name())
        self.save()

    def new_room_action(self):
        if self.game is None: return
        self.tabs.setCurrentWidget(self.room_info_tab)
        r_name, entered = QInputDialog.getText(self, 'New room', 'Enter room name')
        if not entered: return
        if self.game.exists_room_with_name(r_name):
            # TODO show error
            return
        room_li = RoomLI(r_name)
        room = room_li.room
        self.game.rooms += [room]
        self.rooms_listw.addItem(room_li)
        self.rooms_listw.setItemWidget(room_li, room_li.label)
        self.room_info_tab.setFocus()
        self.update_rooms_list()
        self.current_room = room_li
        self.r_widget.setEnabled(True)
        self.update_room_panel()
        if self.game.spawn_room is None:
            self.chosen_spawn_room_action()

    def update_room_panel(self):
        self.tiles_list.clear()

        for tile in self.current_room.room.tileset:
            self.add_tile_to_list(tile)

    def room_clicked_action(self, item):
        self.current_room = item
        self.update_room_panel()
        
        layout = self.tiles_layout.widget().layout()
        while layout.count() > 0: 
            layout.itemAt(0).widget().setParent(None)
        room = item.room
        for i in range(len(room.layout)):
            for j in range(len(room.layout[0])):
                w = TileWidget(self, room.layout[i][j])
                layout.addWidget(w, j, i)
                w.x_pos = j
                w.y_pos = i

    def delete_room_action(self):
        pass
    
    def edit_tile_action(self):
        if self.game is None: return
        i = self.tiles_list.selectedIndexes()
        s: list[TileLI] = self.tiles_list.selectedItems()
        if len(s) != 1: return
        i = i[0].row()
        self.tile_editor.load(s[0].tile)
        self.tile_editor.exec_()
        if not self.tile_editor.saved: return
        tile = self.tile_editor.pack()
        self.current_room.room.tileset[i].copy(tile)
        tile = self.current_room.room.tileset[i]
        layout = self.current_room.room.layout
        for i in range(len(layout)):
            for j in range(len(layout[0])):
                if layout[i][j] != tile: continue
                t: TileWidget = self.tiles_layout.tiles_layout.itemAtPosition(i, j).widget()
                t.setPixmap(tile.image)
        self.invalidate_saved()

    def new_tile_action(self):
        if self.game is None: return
        if self.current_room is None: return
        self.tile_editor.unload()
        self.tile_editor.exec_()
        if not self.tile_editor.saved: return
        tile = self.tile_editor.pack()
        self.current_room.room.tileset += [tile]
        self.add_tile_to_list(tile)
        self.invalidate_saved()

    def chosen_spawn_room_action(self):
        room_name = self.game_rooms_list.currentText()
        for r in self.game.rooms:
            if r.name() == room_name:
                self.game.spawn_room = r
                return
        raise Exception('Err: can\'t set non-existing room with name "' + room_name + '" as spawn room')

    # events
    def closeEvent(self, e) -> None:
        if not self.saved and not self.yn('Closing', 'Are you sure you want to quit? Unsaved changes will be discarded.'):
            e.ignore()
            return
        e.accept()

    def keyPressEvent(self, e: QKeyEvent) -> None:
        modifiers = QApplication.keyboardModifiers()
        is_room = self.tabs.currentWidget() == self.room_info_tab
        if e.key() == Qt.Key_Space:
            items = self.tiles_list.selectedItems()
            if len(items) == 1:
                item: TileLI = items[0]
                t = item.tile
                layout = self.current_room.room.layout
                image = t.image
                tiles = self.get_selected_tiles()
                for tile in tiles:
                    tile.setPixmap(image)
                    layout[tile.y_pos][tile.x_pos] = t
                self.invalidate_saved()
        if e.key() == Qt.Key_A and modifiers == Qt.ControlModifier and is_room:
            self.first_selected_tile = self.tiles_layout.tiles_layout.itemAtPosition(0, 0).widget()
            height = self.tiles_layout.y_count
            width = self.tiles_layout.x_count
            self.second_selected_tile = self.tiles_layout.tiles_layout.itemAtPosition(width-1, height-1).widget()
            self.select_tiles()
        if e.key() == Qt.Key_S and modifiers == Qt.AltModifier and is_room:
            if not (self.first_selected_tile is not None and self.second_selected_tile is None): return
            if self.current_room is None: return
            self.game.spawn_room = self.current_room.room
            self.spawn_x_edit.setText(str(self.first_selected_tile.x_pos))
            self.spawn_y_edit.setText(str(self.first_selected_tile.y_pos))
            self.mb('Spawn set')
        return super().keyPressEvent(e)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Creator()
    ex.show()
    sys.exit(app.exec_())

'''
Images don't load neither in the list of tiles nor in the tiles grid
'''

        # self.installEventFilter(self)

    # def mousePressEvent(self, e) -> None:
    #     if e.type() == QEvent.MouseButtonPress:
    #         if e.button() == Qt.RightButton:
    #             print(e.globalPos())
    #             self.open_context_menu()
    #     return super().mousePressEvent(e)

    # def open_context_menu(self):
    #     print('ampgis')

    # def eventFilter(self, object: QObject, event: QEvent) -> bool:
    #     if event.type() == QEvent.ContextMenu:
    #         # print(event.globalPos())
    #         print(self.childAt(event.globalPos()))
    #         # print('amogus')
    #     return super().eventFilter(object, event)