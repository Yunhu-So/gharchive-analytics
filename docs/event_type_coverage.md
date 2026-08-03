# Event type coverage

Generated from ingested bronze data spanning 2015-01-01 00:00:00 to 2015-09-21 23:59:59.

| type | first seen | last seen | event count |
|---|---|---|---|
| PushEvent | 2015-01-01 00:00:00 | 2015-09-21 23:59:59 | 70,798,458 |
| CreateEvent | 2015-01-01 00:00:01 | 2015-09-21 23:59:59 | 19,475,693 |
| IssueCommentEvent | 2015-01-01 00:00:06 | 2015-09-21 23:59:58 | 13,379,250 |
| PullRequestReviewCommentEvent | 2015-01-01 00:00:08 | 2015-09-21 23:59:55 | 2,362,611 |
| PullRequestEvent | 2015-01-01 00:00:11 | 2015-09-21 23:59:58 | 7,182,326 |
| ForkEvent | 2015-01-01 00:00:16 | 2015-09-21 23:59:58 | 4,814,473 |
| WatchEvent | 2015-01-01 00:00:18 | 2015-09-21 23:59:58 | 12,795,988 |
| DeleteEvent | 2015-01-01 00:00:30 | 2015-09-21 23:59:59 | 3,025,019 |
| IssuesEvent | 2015-01-01 00:00:30 | 2015-09-21 23:59:59 | 6,883,255 |
| CommitCommentEvent | 2015-01-01 00:00:55 | 2015-09-21 23:59:35 | 921,462 |
| GollumEvent | 2015-01-01 00:01:10 | 2015-09-21 23:59:41 | 1,342,970 |
| ReleaseEvent | 2015-01-01 00:02:19 | 2015-09-21 23:59:47 | 476,038 |
| MemberEvent | 2015-01-01 00:04:11 | 2015-09-21 23:59:39 | 697,550 |
| PublicEvent | 2015-01-01 00:09:13 | 2015-09-21 23:57:30 | 139,717 |

A type whose first-seen date falls after the ingested range's start entered the Events API later than that point; a type whose last-seen date falls before the range's end stopped being emitted before that point. Either case means a time series spanning that type's absence would misread instrumentation change as a real trend (see README caveats and section 7.3 of the build brief).

## Known event types absent from this range

Zero events of these types appear anywhere in the ingested range above. For a type that launched after this range's end (e.g. PullRequestReviewEvent, which GitHub introduced with its 2016 formal-review UI), this is expected, not a gap -- confirm against GitHub's own type history before treating it as one:

- PullRequestReviewEvent
- PullRequestReviewThreadEvent
- SponsorshipEvent

