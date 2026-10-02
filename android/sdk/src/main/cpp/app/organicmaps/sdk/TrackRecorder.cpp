#include "Framework.hpp"

#include "app/organicmaps/sdk/bookmarks/data/ElevationInfo.hpp"
#include "app/organicmaps/sdk/core/jni_helper.hpp"

#include "map/gps_tracker.hpp"
#include "geometry/mercator.hpp"
#include "geometry/simplification.hpp"

#include <chrono>

extern "C"
{
// Routing anchors only. The canonical recorded track is neither modified nor truncated.
JNIEXPORT jintArray Java_app_organicmaps_sdk_location_TrackRecorder_nativeRouteOsTrackWaypointIndices(
    JNIEnv * env, jclass, jdoubleArray coordinates)
{
  auto const count = env->GetArrayLength(coordinates) / 2;
  std::vector<jint> indices;
  if (count <= 101)
  {
    for (jint i = 0; i < count; ++i) indices.push_back(i);
  }
  else
  {
    std::vector<double> values(count * 2);
    env->GetDoubleArrayRegion(coordinates, 0, count * 2, values.data());
    std::vector<m2::PointD> points;
    points.reserve(count);
    for (int i = 0; i < count; ++i) points.push_back(mercator::FromLatLon(values[i * 2], values[i * 2 + 1]));
    double epsilon = 1e-8;
    do
    {
      indices.clear();
      SimplifyDP(points.begin(), points.end(), epsilon, m2::SquaredDistanceFromSegmentToPoint{},
                 [&](m2::PointD const & point) { indices.push_back(static_cast<jint>(&point - points.data())); });
      epsilon *= 4;
    } while (indices.size() > 101);
  }
  auto result = env->NewIntArray(indices.size());
  if (!indices.empty()) env->SetIntArrayRegion(result, 0, indices.size(), indices.data());
  return result;
}

JNIEXPORT jdoubleArray Java_app_organicmaps_sdk_location_TrackRecorder_nativeRouteOsGetRecordedPoints(JNIEnv * env, jclass)
{
  auto & tracker = GpsTracker::Instance();
  auto const count = tracker.Finalize();
  std::vector<double> points;
  points.reserve(count * 4);
  if (count > 0)
    tracker.ForEachTrackPoint([&points](location::GpsInfo const & point, size_t) {
      points.insert(points.end(), {point.m_latitude, point.m_longitude, point.m_timestamp, point.m_altitude});
      return true;
    });
  auto result = env->NewDoubleArray(points.size());
  if (!points.empty()) env->SetDoubleArrayRegion(result, 0, points.size(), points.data());
  return result;
}

JNIEXPORT void Java_app_organicmaps_sdk_location_TrackRecorder_nativeStartTrackRecording(JNIEnv * env, jclass clazz)
{
  frm()->StartTrackRecording();
}

JNIEXPORT void Java_app_organicmaps_sdk_location_TrackRecorder_nativeSetTrackRecordingStatsListener(
    JNIEnv * env, jclass clazz, jobject updateListener)
{
  if (updateListener == nullptr)
  {
    frm()->SetTrackRecordingUpdateHandler(nullptr);
    return;
  }
  ASSERT(frm()->IsTrackRecordingEnabled(), ());
  static jmethodID const cId = jni::GetConstructorID(env, g_trackStatisticsClazz, "(DDDDII)V");

  frm()->SetTrackRecordingUpdateHandler(
      [listener = jni::make_global_ref(updateListener)](TrackStatistics const & trackStats)
  {
    // The handler is a platform::SafeCallback, so it always runs on the attached GUI thread.
    JNIEnv * env = jni::GetEnv();
    jobject stats =
        env->NewObject(g_trackStatisticsClazz, cId, trackStats.m_length, trackStats.m_duration, trackStats.m_ascent,
                       trackStats.m_descent, trackStats.m_minElevation, static_cast<jint>(trackStats.m_maxElevation));

    jmethodID onUpdateFn = jni::GetMethodID(env, *listener, "onTrackRecordingUpdate",
                                            "(Lapp/organicmaps/sdk/bookmarks/data/TrackStatistics;)V");
    env->CallVoidMethod(*listener, onUpdateFn, stats);
    jni::HandleJavaException(env);
  });
}

JNIEXPORT jobject Java_app_organicmaps_sdk_location_TrackRecorder_nativeGetElevationInfo(JNIEnv * env, jclass clazz)
{
  ASSERT(frm()->IsTrackRecordingEnabled(), ("Track recording is not started"));
  if (frm()->IsTrackRecordingEmpty())
    return nullptr;
  return ToJavaElevationInfo(env, frm()->GetTrackRecordingElevationInfo());
}

JNIEXPORT void Java_app_organicmaps_sdk_location_TrackRecorder_nativeStopTrackRecording(JNIEnv * env, jclass clazz)
{
  frm()->StopTrackRecording();
}

JNIEXPORT void Java_app_organicmaps_sdk_location_TrackRecorder_nativeSaveTrackRecordingWithName(JNIEnv * env,
                                                                                                jclass clazz,
                                                                                                jstring name)
{
  frm()->SaveTrackRecordingWithName(jni::ToNativeString(env, name));
}

JNIEXPORT jboolean Java_app_organicmaps_sdk_location_TrackRecorder_nativeIsTrackRecordingEmpty(JNIEnv * env,
                                                                                               jclass clazz)
{
  return frm()->IsTrackRecordingEmpty();
}

JNIEXPORT jboolean Java_app_organicmaps_sdk_location_TrackRecorder_nativeIsTrackRecordingEnabled(JNIEnv * env,
                                                                                                 jclass clazz)
{
  return frm()->IsTrackRecordingEnabled();
}
}  // namespace
