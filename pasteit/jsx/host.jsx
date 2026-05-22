// jsx/host.jsx

function importAndPlace(filePath) {
  if (!app.project) return "ERROR:no_project";

  var seq = app.project.activeSequence;
  if (!seq) return "ERROR:no_sequence";

  if (seq.videoTracks.numTracks === 0) return "ERROR:no_video_track";

  // Record count before import to locate new item by position fallback
  var countBefore = app.project.rootItem.children.numItems;

  // importFiles(paths, suppressUI, targetBin, importAsNumberedStills)
  var ok = app.project.importFiles([filePath], true, app.project.rootItem, false);
  if (!ok) return "ERROR:import_failed";

  // Locate the imported item by path, fall back to last item if count grew
  var projectItems = app.project.rootItem.children;
  var importedItem = null;

  for (var i = 0; i < projectItems.numItems; i++) {
    try {
      if (projectItems[i].getMediaPath() === filePath) {
        importedItem = projectItems[i];
        break;
      }
    } catch (e) {}
  }

  if (!importedItem && projectItems.numItems > countBefore) {
    importedItem = projectItems[projectItems.numItems - 1];
  }

  if (!importedItem) return "ERROR:item_not_found";

  var playheadTime = seq.getPlayerPosition();
  var insertedClip = seq.videoTracks[0].insertClip(importedItem, playheadTime);

  // Set duration to 5 seconds from the clip's actual start position
  if (insertedClip) {
    var endTime = new Time();
    endTime.seconds = insertedClip.start.seconds + 5.0;
    insertedClip.end = endTime;
  }

  return "OK";
}
