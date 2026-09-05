#include "platform.h"
QList<Application> discoverApplications() { return {}; }
QImage applicationIcon(const QString &) { return {}; }
bool openApplication(const QString &, QString &error) { error="此平台的应用适配器尚未实现。"; return false; }
