#include "catalog.h"
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLocalSocket>
#include <QUrl>

namespace {
constexpr auto xdockLaunchEventServer = "ai-workspace-lab.xdock.launch-events";

void notifyXDock(const Application &app) {
    QLocalSocket socket;
    socket.connectToServer(QString::fromLatin1(xdockLaunchEventServer));
    if (!socket.waitForConnected(150)) return;
    const auto encodedPath = QString::fromLatin1(QUrl::toPercentEncoding(app.path));
    const QJsonObject event{{"type", "launched"}, {"name", app.name},
                            {"launchId", app.path}, {"icon", "path:" + encodedPath}};
    socket.write(QJsonDocument(event).toJson(QJsonDocument::Compact));
    socket.write("\n");
    socket.waitForBytesWritten(150);
}
}

Catalog::Catalog(){refresh();}
void Catalog::refresh(){apps=discoverApplications();filter();}
void Catalog::setQuery(QString q){if(q==m_query)return;m_query=q;filter();}
void Catalog::setCategory(QString c){if(c==m_category)return;m_category=c;filter();}
void Catalog::filter(){
 beginResetModel();visible.clear();
 for(int i=0;i<apps.size();++i) if((m_category=="全部"||apps[i].category==m_category)&&(apps[i].name.contains(m_query.trimmed(),Qt::CaseInsensitive)||QFileInfo(apps[i].path).completeBaseName().contains(m_query.trimmed(),Qt::CaseInsensitive))) visible.append(i);
 endResetModel();++generation;emit filterChanged();
}
QVariant Catalog::data(const QModelIndex &index,int role) const{
 if(!index.isValid()||index.row()<0||index.row()>=visible.size())return {};
 int i=visible[index.row()]; const auto &a=apps[i];
 if(role==Name)return a.name;if(role==Icon)return QString("image://apps/%1").arg(i);if(role==Path)return a.path;return {};
}
QHash<int,QByteArray> Catalog::roleNames()const{return {{Name,"appName"},{Icon,"appIcon"},{Path,"appPath"}};}
QVariantList Catalog::page(int start,int size)const{
 QVariantList result;
 for(int row=qMax(0,start);row<qMin(start+size,visible.size());++row)
   result.append(QVariantMap{{"name",data(index(row),Name)},{"icon",data(index(row),Icon)},{"row",row}});
 return result;
}
bool Catalog::launch(int row){
 if(row<0||row>=visible.size())return false;
 const auto &app=apps[visible[row]];
 QString error; if(openApplication(app.path,error)){notifyXDock(app);emit launched();return true;}emit failure(error);return false;
}
