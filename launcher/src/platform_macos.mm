#include "platform.h"
#import <AppKit/AppKit.h>
#include <QDirIterator>
#include <QSet>
#include <algorithm>

static QString categoryFor(NSString *value) {
    QString c = QString::fromNSString(value ?: @"");
    if(c.contains("developer")) return "开发";
    if(c.contains("game")) return "游戏";
    if(c.contains("graphics") || c.contains("photography") || c.contains("design")) return "图形";
    if(c.contains("music") || c.contains("video") || c.contains("entertainment")) return "多媒体";
    if(c.contains("productivity") || c.contains("business") || c.contains("finance")) return "办公";
    if(c.contains("social") || c.contains("news") || c.contains("travel")) return "网络";
    return "工具";
}
QList<Application> discoverApplications() {
    QList<Application> apps; QSet<QString> seen;
    @autoreleasepool {
      for(const QString &root : {QString("/Applications"), QDir::homePath()+"/Applications", QString("/System/Applications"), QString("/System/Library/CoreServices/Applications"), QString("/System/Cryptexes/App/System/Applications")}) {
        // Prune bundles: helpers inside an app are not independent launch targets.
        QList<QString> pending{root};
        while(!pending.isEmpty()) {
          QDir dir(pending.takeLast());
          for(const QFileInfo &entry : dir.entryInfoList(QDir::Dirs|QDir::NoDotAndDotDot)) {
            if(!entry.fileName().endsWith(".app", Qt::CaseInsensitive)) { if(!entry.isSymLink()) pending.append(entry.absoluteFilePath()); continue; }
            QString path=entry.canonicalFilePath(); if(seen.contains(path)) continue;
            NSBundle *bundle=[NSBundle bundleWithPath:path.toNSString()];
            if(!bundle) continue;
            seen.insert(path);
            NSString *name=[bundle objectForInfoDictionaryKey:@"CFBundleDisplayName"] ?: [bundle objectForInfoDictionaryKey:@"CFBundleName"];
            Application app; app.path=path; app.name=name ? QString::fromNSString(name) : entry.completeBaseName();
            app.category=categoryFor([bundle objectForInfoDictionaryKey:@"LSApplicationCategoryType"]);
            if(path.startsWith("/System/") && app.category=="工具") app.category="系统";
            if(app.name.contains("Safari") || app.name.contains("Firefox") || app.name.contains("Chrome")) app.category="网络";
            apps.append(app);
          }
        }
      }
    }
    std::sort(apps.begin(),apps.end(),[](const auto &a,const auto &b){return a.name.localeAwareCompare(b.name)<0;});
    return apps;
}
bool openApplication(const QString &path, QString &error) {
    // LaunchServices handles bundle execution; no shell interpolation.
    BOOL ok=[[NSWorkspace sharedWorkspace] openURL:[NSURL fileURLWithPath:path.toNSString()]];
    if(!ok) error="无法打开应用，请检查应用是否已移动或被系统阻止。";
    return ok;
}

QImage applicationIcon(const QString &path) {
 QImage result;
 @autoreleasepool {
            NSImage *icon=[[NSWorkspace sharedWorkspace] iconForFile:path.toNSString()];
            [icon setSize:NSMakeSize(96,96)];
            NSRect rect=NSMakeRect(0,0,96,96);
            CGImageRef cg=[icon CGImageForProposedRect:&rect context:nil hints:nil];
            if(cg) {
              NSBitmapImageRep *rep=[[NSBitmapImageRep alloc] initWithCGImage:cg];
              NSData *png=[rep representationUsingType:NSBitmapImageFileTypePNG properties:@{}];
              result.loadFromData((const uchar*)png.bytes, png.length, "PNG");
              [rep release];
            }

 }
 return result;
}
