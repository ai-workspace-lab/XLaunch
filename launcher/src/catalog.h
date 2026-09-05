#pragma once
#include "platform.h"
#include <QAbstractListModel>
#include <QQuickImageProvider>
class Catalog : public QAbstractListModel {
 Q_OBJECT
 Q_PROPERTY(QString query READ query WRITE setQuery NOTIFY filterChanged)
 Q_PROPERTY(QString category READ category WRITE setCategory NOTIFY filterChanged)
 Q_PROPERTY(int count READ rowCount NOTIFY filterChanged)
 Q_PROPERTY(int revision READ revision NOTIFY filterChanged)
 public:
 enum Roles {Name=Qt::UserRole+1, Icon, Path};
 QList<Application> apps; QList<int> visible;
 QString m_query,m_category="全部";
 Catalog();
 int rowCount(const QModelIndex &parent={}) const override { return parent.isValid()?0:visible.size(); }
 QVariant data(const QModelIndex &,int) const override;
 QHash<int,QByteArray> roleNames() const override;
 QString query() const{return m_query;} QString category() const{return m_category;}
 void setQuery(QString); void setCategory(QString);
 Q_INVOKABLE void refresh();
 Q_INVOKABLE bool launch(int row);
 int generation=0;
 int revision() const {return generation;}
 Q_INVOKABLE QVariantList page(int start,int size) const;
 signals: void filterChanged(); void launched(); void failure(QString message);
 private: void filter();
};
class Icons : public QQuickImageProvider {
 Catalog *catalog;
 public: Icons(Catalog *c):QQuickImageProvider(Image),catalog(c){}
 QImage requestImage(const QString &id,QSize *size,const QSize &) override {
   bool ok; int index=id.toInt(&ok); QImage image;
   if(ok && index>=0 && index<catalog->apps.size()) {
     auto &app=catalog->apps[index];
     if(app.icon.isNull()) app.icon=applicationIcon(app.path);
     image=app.icon;
   }
   if(size) *size=image.size(); return image;
 }
};
