import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
 id: root
 visible: true
 width: 1448; height: 1086
 visibility: Window.Maximized
 flags: Qt.Window | Qt.FramelessWindowHint
 title: "XLaunch"
 color: "#513b27"
 property string notice: ""
 property bool systemTheme: false
 readonly property color foreground: systemTheme ? palette.windowText : "#fff9eb"
 readonly property color secondary: systemTheme ? palette.placeholderText : "#dfd0ba"
 property real uiScale: Math.max(0.75, Math.min(width / 1448, height / 1086))
 Image { anchors.fill: parent; visible:!root.systemTheme;source: "../assets/amber-wallpaper.png"; fillMode: Image.PreserveAspectCrop }
 Rectangle { anchors.fill: parent; color: root.systemTheme?root.palette.window:"#18000000" }
 Label { x: 26; y: 24; text: "XLaunch"; color: root.foreground; font.pixelSize: 19 }
 TextField {
  id: search
  anchors.top: parent.top; anchors.topMargin: 54 * root.uiScale
  anchors.horizontalCenter: parent.horizontalCenter
  width: Math.min(parent.width * 0.56, 780); height: 58 * root.uiScale
  color: root.foreground; font.pixelSize: 21 * root.uiScale
  placeholderText: "搜索应用、系统操作，或描述任务…"; placeholderTextColor: root.secondary
  leftPadding: 22; rightPadding: 18; selectByMouse: true; focus: true
  background: Rectangle { radius: 8; color: root.systemTheme?root.palette.base:"#28ffffff"; border.color: root.systemTheme?(search.activeFocus?root.palette.highlight:root.palette.mid):(search.activeFocus ? "#b6dfc19a" : "#70ffffff"); border.width: 1 }
  onTextChanged: {catalog.query=text; grid.currentIndex=0; pages.currentIndex=0; root.notice=""}
  Keys.onDownPressed: {grid.forceActiveFocus();grid.currentIndex=0}
  onAccepted: catalog.launch(grid.currentIndex)
 }
 Label {
  anchors.top: search.bottom; anchors.topMargin: 16; anchors.horizontalCenter: search.horizontalCenter
  text: search.text.length ? catalog.count + " 个应用" : "输入应用名称搜索 · AI 与系统指令将在后续版本接入"
  color: root.secondary;font.pixelSize: 14
 }
 RowLayout {
  anchors {left: parent.left;right:parent.right;top:search.bottom;bottom:footer.top;topMargin:54*root.uiScale;bottomMargin:20;leftMargin:26;rightMargin:30}
  spacing: 26
  ColumnLayout {
   Layout.preferredWidth: 184 * root.uiScale;Layout.maximumWidth:184 * root.uiScale;Layout.minimumWidth:184 * root.uiScale;Layout.fillHeight:true;spacing:8
   Repeater {
    model: ["全部","网络","多媒体","游戏","图形","办公","开发","系统","工具","AI"]
    delegate: Button {
     required property string modelData
     Layout.fillWidth:true;Layout.preferredHeight:58*root.uiScale
     text:modelData
     contentItem: Label {text:parent.text;color: root.systemTheme&&catalog.category===modelData?root.palette.highlightedText:root.foreground;font.pixelSize:21*root.uiScale;verticalAlignment:Text.AlignVCenter;leftPadding:22}
     background: Rectangle {radius:6;color:catalog.category===modelData?(root.systemTheme?root.palette.highlight:"#32ffffff"):parent.hovered?(root.systemTheme?root.palette.alternateBase:"#15ffffff"):"transparent";border.color:catalog.category===modelData?(root.systemTheme?root.palette.highlight:"#50fff2d6"):"transparent"}
     onClicked:{catalog.category=modelData;grid.currentIndex=0;pages.currentIndex=0}
    }
   }
   Item {Layout.fillHeight:true}
  }
  Rectangle {Layout.fillHeight:true;Layout.preferredWidth:1;color:root.systemTheme?root.palette.mid:"#45fce2b1"}
  Item {
   Layout.fillWidth:true;Layout.fillHeight:true
   Item {
    id:grid;anchors.fill:parent
    property int currentIndex:0
    readonly property int columns:Math.max(3,Math.min(9,Math.floor(width/140)))
    readonly property int pageSize:columns*5
    function select(delta) {
     currentIndex=Math.max(0,Math.min(catalog.count-1,currentIndex+delta))
     pages.currentIndex=Math.floor(currentIndex/pageSize)
    }
    ListView {
     id:pages;anchors {fill:parent;bottomMargin:30} clip:true
     orientation:ListView.Horizontal;snapMode:ListView.SnapOneItem
     boundsBehavior:Flickable.StopAtBounds;highlightRangeMode:ListView.StrictlyEnforceRange
     highlightMoveDuration:180;model:Math.ceil(catalog.count/grid.pageSize)
     onMovementEnded:grid.currentIndex=currentIndex*grid.pageSize
     delegate:Item {
      id:pageItem;required property int index;width:pages.width;height:pages.height
      Grid {
       anchors.fill:parent;columns:grid.columns
       Repeater {
        model:{let revision=catalog.revision;return catalog.page(pageItem.index*grid.pageSize,grid.pageSize)}
        delegate:Item {
         required property var modelData
         width:pages.width/grid.columns;height:pages.height/5
         Accessible.role:Accessible.Button;Accessible.name:modelData.name
         Accessible.onPressAction:catalog.launch(modelData.row)
         Rectangle {anchors.fill:parent;anchors.margins:6;radius:5;color:(grid.currentIndex===modelData.row&&grid.activeFocus)||mouse.containsMouse?(root.systemTheme?root.palette.alternateBase:"#20ffffff"):"transparent";border.color:grid.currentIndex===modelData.row&&grid.activeFocus?(root.systemTheme?root.palette.highlight:"#80ffffff"):"transparent"}
         Image {anchors.horizontalCenter:parent.horizontalCenter;y:8*root.uiScale;width:76*root.uiScale;height:76*root.uiScale;source:modelData.icon;sourceSize:Qt.size(96,96);fillMode:Image.PreserveAspectFit}
         Label {anchors.horizontalCenter:parent.horizontalCenter;y:94*root.uiScale;width:parent.width-10;text:modelData.name;color:root.foreground;font.pixelSize:17*root.uiScale;horizontalAlignment:Text.AlignHCenter;elide:Text.ElideRight;maximumLineCount:2;wrapMode:Text.Wrap}
         MouseArea {id:mouse;anchors.fill:parent;hoverEnabled:true;onClicked:{grid.currentIndex=modelData.row;catalog.launch(modelData.row)}}
        }
       }
      }
     }
    }
    PageIndicator {id:pageDots;anchors.bottom:parent.bottom;anchors.horizontalCenter:parent.horizontalCenter;count:pages.count;currentIndex:pages.currentIndex;interactive:true;onCurrentIndexChanged:{pages.currentIndex=currentIndex;if(Math.floor(grid.currentIndex/grid.pageSize)!==currentIndex)grid.currentIndex=currentIndex*grid.pageSize}
     delegate:Rectangle {required property int index;implicitWidth:8;implicitHeight:8;radius:4;color:root.foreground;opacity:index===pageDots.currentIndex?0.95:0.35}}
    Keys.onLeftPressed:select(-1)
    Keys.onRightPressed:select(1)
    Keys.onUpPressed:select(-columns)
    Keys.onDownPressed:select(columns)
    Keys.onReturnPressed:catalog.launch(currentIndex)
    Keys.onEnterPressed:catalog.launch(currentIndex)
    Keys.onPressed:function(event){if(event.text.length&&!(event.modifiers&(Qt.ControlModifier|Qt.MetaModifier))){search.forceActiveFocus();search.text+=event.text;event.accepted=true}}
   }
   Label {anchors.centerIn:parent;visible:catalog.count===0;text:catalog.category==="AI"?"Agent 尚未连接\n请切换到“全部”浏览本机应用": "没有匹配的应用\n尝试其他名称或分类";color:root.foreground;font.pixelSize:20;horizontalAlignment:Text.AlignHCenter}
  }
 }
 Label {id:footer;anchors.bottom:parent.bottom;anchors.bottomMargin:28;anchors.horizontalCenter:parent.horizontalCenter;text:root.notice.length?root.notice:"左右拖动翻页     方向键 选择     Enter 打开     Esc 关闭";color:root.secondary;font.pixelSize:16}
 Shortcut {sequence:"Escape";onActivated:{if(search.text.length){search.clear();search.forceActiveFocus()}else root.hide()}}
 Shortcut {sequence:"Ctrl+F";onActivated:search.forceActiveFocus()}
 Shortcut {sequence:"Meta+F";onActivated:search.forceActiveFocus()}
 Shortcut {sequence:"Ctrl+R";onActivated:catalog.refresh()}
 onVisibleChanged:if(visible){search.clear();catalog.category="全部";grid.currentIndex=0;pages.currentIndex=0;search.forceActiveFocus()}
 Shortcut {sequence:"Ctrl+Right";onActivated:{pages.currentIndex=Math.min(pages.count-1,pages.currentIndex+1);grid.currentIndex=pages.currentIndex*grid.pageSize}}
 Shortcut {sequence:"Ctrl+Left";onActivated:{pages.currentIndex=Math.max(0,pages.currentIndex-1);grid.currentIndex=pages.currentIndex*grid.pageSize}}
 Connections {target:catalog;function onFailure(message){root.notice=message}}
}
