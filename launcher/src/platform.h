#pragma once
#include <QImage>
#include <QString>
#include <QList>
struct Application { QString name, path, category; QImage icon; };
QList<Application> discoverApplications();
bool openApplication(const QString &path, QString &error);
QImage applicationIcon(const QString &path);
