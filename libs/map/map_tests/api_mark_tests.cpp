#include "testing/testing.hpp"

#include "map/api_mark_point.hpp"
#include "map/framework.hpp"

#include "geometry/mercator.hpp"

#include <string>

namespace api_mark_tests
{
// Returns the single API mark parsed from an om:// deep link. ExecuteMapApiRequest()
// materializes the marks described by the URL into the API user-mark group.
ApiMarkPoint const * CreateSingleApiMark(Framework & fm, std::string const & url)
{
  TEST_EQUAL(fm.ParseAndSetApiURL(url), url_scheme::ParsedMapApi::UrlType::Map, (url));
  fm.ExecuteMapApiRequest();
  auto const & ids = fm.GetBookmarkManager().GetUserMarkIds(UserMark::Type::API);
  TEST_EQUAL(ids.size(), 1, (url));
  return fm.GetBookmarkManager().GetMark<ApiMarkPoint>(*ids.begin());
}

// The per-point "id" and the global "backurl" are independent API inputs: a request may
// carry either, both, or neither. FillApiMarkInfo() copies the mark's GetApiID() and
// GenerateApiBackUrl() into place_page::Info::GetApiId()/GetApiUrl() respectively -- the
// two values the place page surfaces, with the id returned to the caller (Android
// EXTRA_POINT_ID). This pins down that the id is surfaced independently of the back URL.
UNIT_TEST(ApiPoint_PointIdIsIndependentOfBackUrl)
{
  Framework fm(FrameworkParams(false /* m_enableDiffs */));

  // id without backurl: id present, back URL empty.
  {
    auto const * mark = CreateSingleApiMark(fm, "om://map?ll=1,2&id=foo");
    TEST_EQUAL(mark->GetApiID(), "foo", ());
    TEST(fm.GenerateApiBackUrl(*mark).empty(), ("No backurl -> empty back URL, id still present"));
  }

  // backurl without id: a back URL but no point id to echo back.
  {
    auto const * mark = CreateSingleApiMark(fm, "om://map?ll=1,2&backurl=testapp");
    TEST(mark->GetApiID().empty(), ("No id -> empty point id"));
    TEST(!fm.GenerateApiBackUrl(*mark).empty(), ());
  }

  // Both present: the point id and the back URL are distinct, separately surfaced fields.
  {
    auto const * mark = CreateSingleApiMark(fm, "om://map?ll=1,2&id=foo&backurl=testapp");
    TEST_EQUAL(mark->GetApiID(), "foo", ());
    TEST_NOT_EQUAL(mark->GetApiID(), fm.GenerateApiBackUrl(*mark), ("point id and back URL are distinct"));
  }
}

UNIT_TEST(ApiPoint_PositionCanBeUpdatedWithoutRecreatingTheMark)
{
  Framework fm(FrameworkParams(false /* m_enableDiffs */));
  CreateSingleApiMark(fm, "om://map?ll=1,2&id=driver-7");
  auto const markId = *fm.GetBookmarkManager().GetUserMarkIds(UserMark::Type::API).begin();
  {
    auto session = fm.GetBookmarkManager().GetEditSession();
    session.GetMarkForEdit<ApiMarkPoint>(markId)->SetPosition(mercator::FromLatLon(10.5, 77.25));
  }
  auto const * updated = fm.GetBookmarkManager().GetMark<ApiMarkPoint>(markId);
  TEST_EQUAL(updated->GetApiID(), "driver-7", ());
  TEST_ALMOST_EQUAL_ABS(updated->GetLatLon().m_lat, 10.5, 1e-6, ());
  TEST_ALMOST_EQUAL_ABS(updated->GetLatLon().m_lon, 77.25, 1e-6, ());
}
}  // namespace api_mark_tests
