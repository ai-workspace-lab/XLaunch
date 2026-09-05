#include "catalog.h"
#include <QFileInfo>
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
 QString error; if(openApplication(apps[visible[row]].path,error)){emit launched();return true;}emit failure(error);return false;
}
