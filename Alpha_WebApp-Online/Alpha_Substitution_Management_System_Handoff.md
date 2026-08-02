# Alpha Substitution Management System

# Owner - S Karthikeyan All Copyrights Reserved , Contact - s.karthikeyan2820@gmail.com
# Database All Copyrights Reserved By Alpha Groups Of Institutions

## Comprehensive Developer Handoff
**Last Updated** 10 July 2026\
**Hours Spent:** ~ 300 Hours\
**Document date:** 1 July 2026\
**Project:** Alpha Substitution Management System\
**Technology:** Python, Flask, Oracle MySQL, HTML, CSS, Bootstrap\
**Purpose:** Operational and developer handoff for maintenance, testing,
deployment, and future development.

------------------------------------------------------------------------

## 1. Executive Summary

The Alpha Substitution Management System is a web application developed
to manage teacher records, timetables, absences, substitute-teacher
candidate generation, VP review and finalization, teacher dashboards,
authentication, reporting, and historical records.

The system evolved from an offline substitution-management concept into
a Flask/MySQL web application. The current database contains
approximately 90 teachers and their timetables. The application supports
an administrator/VP workflow and teacher-facing access.

A major recent engineering focus was performance. The original
substitution workflow repeatedly opened MySQL connections inside nested
teacher/period loops. This caused thousands of SQL operations and
browser timeouts. The current implementation uses cached substitution
data, batch writes, consolidated dashboard queries, and
transaction-based teacher updates.

------------------------------------------------------------------------

## 2. Current Project Snapshot

### Main project files discovered

``` text
Alpha_WebApp-Online/Alpha_Substitution(26-27).sql
Alpha_WebApp-Online/app.py
Alpha_WebApp-Online/database.py
Alpha_WebApp-Online/templates/absences.html
Alpha_WebApp-Online/templates/add_teacher.html
Alpha_WebApp-Online/templates/change_password.html
Alpha_WebApp-Online/templates/edit_teacher.html
Alpha_WebApp-Online/templates/index.html
Alpha_WebApp-Online/templates/login.html
Alpha_WebApp-Online/templates/my_absences.html
Alpha_WebApp-Online/templates/my_substitutions.html
Alpha_WebApp-Online/templates/my_timetable.html
Alpha_WebApp-Online/templates/preview_substitutions.html
Alpha_WebApp-Online/templates/previous_absences.html
Alpha_WebApp-Online/templates/previous_substitutions.html
Alpha_WebApp-Online/templates/record_absence.html
Alpha_WebApp-Online/templates/staff_password.html
Alpha_WebApp-Online/templates/substitutions.html
Alpha_WebApp-Online/templates/suggest_substitutions.html
Alpha_WebApp-Online/templates/teachers.html
Alpha_WebApp-Online/templates/teacher_dashboard.html
Alpha_WebApp-Online/templates/timetable.html
Alpha_WebApp-Online/templates/today_substitutions.html
Alpha_WebApp-Online/templates/upcoming_absences.html
Alpha_WebApp-Online/templates/upcoming_substitutions.html
Alpha_WebApp-Online/__pycache__/database.cpython-310.pyc
Alpha_WebApp-Online/static/images/school_logo.png
```

### Application scale

-   Flask routes detected: **34**
-   Database/helper functions detected: **80**
-   Teacher population in current operational context: approximately
    **90 teachers**
-   Standard timetable: **5 weekdays × 9 periods**

------------------------------------------------------------------------

## 3. System Architecture

The application follows a conventional Flask architecture:

``` text
Browser
   |
   v
Flask Routes (app.py)
   |
   +---- Authentication / Session Logic
   |
   +---- Admin and Teacher Workflows
   |
   v
Database Layer (database.py)
   |
   v
Oracle MySQL
```

HTML templates provide the user interface. Flask routes process GET and
POST requests, use session data for authentication/authorization, call
database functions, and render templates or redirect users.

------------------------------------------------------------------------

## 4. Technology Stack

-   **Python** --- application language.
-   **Flask** --- web framework and routing.
-   **Oracle MySQL** --- persistent relational database.
-   **mysql-connector-python** --- Python/MySQL connectivity.
-   **HTML/CSS/Bootstrap** --- user interface.
-   **Jinja2** --- server-side HTML templating.
-   **Cloudflare Tunnel** --- remote exposure of the locally hosted
    application where configured.
-   **Excel/PDF export libraries** --- report generation functionality.

------------------------------------------------------------------------

## 5. Authentication and Roles

The system supports role-aware login and sessions.

### Administrator / VP

The administrator workflow includes teacher management, recording
absences, reviewing substitution candidates, finalizing substitutions,
viewing current and previous records, editing substitutions, reports,
exports, dashboard statistics, and password management.

### Teacher

Teacher users can access teacher-specific functionality such as
dashboards, timetables, substitutions, absence information, and password
changes according to the implemented route permissions.

### Security principle

Every protected route should validate session state and role before
exposing administrative or teacher-specific data. Direct URL access must
not bypass authorization.

------------------------------------------------------------------------

## 6. Core Data Model

The application relies on these principal logical entities.

### Teachers

Stores teacher identity and details such as name, subject, and contact
information.

### Timetable

Stores one row per teacher/day with `period1` through `period9`.

### Teacher Classes

Maps teachers to classes they are capable of handling. This table is
critical to candidate eligibility.

### Absences

Stores the absent teacher, date, and day.

### Substitutions

Stores the absence reference, selected substitute teacher (when a
registered teacher is used), period, class, and optional manual
substitute name.

### Users / Authentication Data

Stores credentials and role information required for administrator and
teacher login flows.

------------------------------------------------------------------------

## 7. Teacher Management Workflow

The application supports adding, viewing, searching, and editing
teachers.

The edit workflow updates:

1.  Teacher information.
2.  Capable classes.
3.  Five-day timetable.

### Recent performance optimization

Originally, these operations used three separate functions and therefore
three independent MySQL connections and commits:

``` text
update_teacher()
update_teacher_classes()
update_timetable()
```

The optimized workflow uses a combined `update_teacher_full()`
transaction:

``` text
Open one connection
   |
Update teacher details
   |
Replace teacher-class mappings
   |
Update timetable
   |
Commit once
   |
Close
```

This reduces connection overhead and ensures atomicity. If an operation
fails, the transaction can roll back rather than leaving a partially
updated teacher.

------------------------------------------------------------------------

## 8. Absence Recording Workflow

The operational workflow is:

``` text
VP/Admin selects date and absent teacher(s)
                |
                v
Absence records are created
                |
                v
Candidate generation begins
                |
                v
Suggestion/preview timetable is displayed
```

Duplicate absence handling should prevent the same teacher from being
recorded twice for the same date.

------------------------------------------------------------------------

## 9. Substitution Candidate Generation

Candidate generation is the core scheduling component.

### Candidate eligibility

A candidate teacher is evaluated according to rules including:

-   Candidate is not the absent teacher.
-   Candidate is not absent on the selected date.
-   Candidate is capable of handling the class.
-   Candidate is free during the required period.
-   Candidate is not already assigned another substitution during that
    period.
-   Existing daily substitution load is considered.
-   The configured maximum substitutions per day is considered.
-   Continuous-period workload is evaluated.
-   Candidate scoring considers free periods and existing substitutions.

The configured daily maximum observed during development is:

``` python
MAX_SUBSTITUTIONS_PER_DAY = 4
```

### Candidate scoring

The existing design uses a score concept equivalent to:

``` text
score = number of free periods - substitutions already assigned today
```

Candidates are sorted while considering workload warnings and score.

------------------------------------------------------------------------

## 10. Candidate Generation Performance Redesign

### Original problem

The original implementation called SQL-backed helper functions inside
nested loops.

Conceptually:

``` text
For every occupied period:
    For every teacher:
        Query absence
        Query capable class
        Query timetable/free status
        Query existing assignment
        Query free-period count
        Query substitution count
        Query consecutive-period status
```

With roughly 90 teachers and 9 periods, this produced thousands of SQL
operations for a single absence.

### Symptoms

-   Submit requests taking 10--15+ seconds.
-   Browser timeouts.
-   MySQL connection instability.
-   Poor scaling with multiple absent teachers.

### Current cache-based design

`load_substitution_cache(absence_date, day)` loads required data in a
small number of queries.

The cache contains data conceptually equivalent to:

``` text
teacher_ids
teacher_names
timetables
free_periods
working_periods
teacher_classes
absent_teachers
assigned_periods
substitution_count
```

Candidate checks then run in Python memory rather than repeatedly
querying MySQL.

### Measured improvement during testing

Profiling showed approximately:

``` text
Absence details query: ~0.44 seconds
Cache loading:         ~0.56 seconds
Candidate processing:  ~0.001 seconds
Total generation:      ~1 second
```

The key result is that candidate processing itself became effectively
instantaneous. Remaining time is primarily database connection/query
overhead.

------------------------------------------------------------------------

## 11. Consecutive-Period Logic

The original `has_three_consecutive_periods()` implementation repeatedly
fetched timetable and substitution information.

The optimized cached implementation uses:

``` text
working_periods[teacher_id]
assigned_periods[teacher_id]
```

It copies the teacher's working-period state, applies existing
substitution assignments, simulates the proposed assignment, and checks
the resulting continuous workload without opening a new database
connection.

When assignments are actually generated by an automatic flow, in-memory
assignment counts and periods must be updated immediately so later
decisions see earlier assignments.

Candidate preview generation must not incorrectly mutate finalized
assignment state merely because a teacher appears as a suggestion.

------------------------------------------------------------------------

## 12. Preview and VP Finalization Workflow

The current operational design does **not** automatically finalize
substitutes when absence Submit is clicked.

The correct workflow is:

``` text
Record absence
      |
Generate candidates
      |
Display suggestion timetable
      |
VP reviews each period
      |
VP chooses:
   - Registered teacher
   - Manual substitute name
   - Substitute Not Available
      |
Preview/finalize
      |
Persist substitutions
```

This distinction is important when maintaining the code. Candidate
generation and final substitution insertion are separate stages.

------------------------------------------------------------------------

## 13. Manual Substitute vs Unavailable Logic

Three substitution states exist:

### Registered teacher

``` text
substitute_teacher_id = valid teacher ID
manual_substitute_name = NULL/empty
```

### Manual substitute

``` text
substitute_teacher_id = NULL
manual_substitute_name = entered name
```

Example used during testing:

``` text
Chemistry Teacher
```

### Substitute unavailable

``` text
substitute_teacher_id = NULL
manual_substitute_name = NULL/empty
```

### Important dashboard fix

The original unavailable count checked only:

``` sql
substitute_teacher_id IS NULL
```

This incorrectly counted manually entered substitutes as unavailable.

The corrected condition is conceptually:

``` sql
substitute_teacher_id IS NULL
AND (
    manual_substitute_name IS NULL
    OR TRIM(manual_substitute_name) = ''
)
```

Only the explicit unavailable state should increment the unavailable
dashboard count.

------------------------------------------------------------------------

## 14. Finalization Performance Optimization

### Original implementation

The finalize route looped through preview substitutions and called
`insert_substitution()` for every record.

Each call performed:

``` text
Open connection
Insert
Commit
Close
```

Four records therefore created four connections and four commits.

### Optimized implementation

`insert_substitutions_batch(substitutions)` performs:

``` text
Open one connection
Build values
executemany()
Commit once
Close once
```

The function uses rollback on failure.

### Measured improvement

During testing:

``` text
Before: approximately 5 seconds for 4 records
After:  approximately 1 second for 10 records
```

This confirms that repeated connection creation was a major system-wide
performance bottleneck.

------------------------------------------------------------------------

## 15. Dashboard

The admin home dashboard displays information including:

-   Current date.
-   Total teachers.
-   Today's absences.
-   Today's substitutions.
-   Today's unavailable substitutions.

### Original problem

Each dashboard count opened its own connection.

``` text
count_teachers()
count_absences_today()
count_substitutions_today_dashboard()
count_unavailable_substitutions()
```

### Optimized design

`get_dashboard_stats(date)` opens one connection, executes the count
queries, returns one statistics dictionary, and closes once.

This significantly reduces page-load overhead.

------------------------------------------------------------------------

## 16. Transaction Configuration

The database connection was changed from:

``` python
autocommit=True
```

to:

``` python
autocommit=False
```

### Reason

The application already uses explicit commits for writes. Disabling
autocommit enables proper transactions.

Recommended write pattern:

``` text
Open connection
try:
    Perform related writes
    Commit
except:
    Roll back
    Re-raise error
finally:
    Close cursor
    Close connection
```

### Important maintenance requirement

Every `INSERT`, `UPDATE`, and `DELETE` path must explicitly commit
successful changes.

When adding new database functions, developers must remember this
requirement.

------------------------------------------------------------------------

## 17. MySQL Performance Lesson

The primary bottleneck discovered during testing was not the size of the
database or the 90-teacher dataset.

It was repeated connection creation.

Avoid:

``` text
Loop
  -> connect_db()
  -> query
  -> close()
```

Prefer:

``` text
connect_db()
  -> load required data
  -> process in memory
  -> batch writes
  -> commit
  -> close
```

This principle should guide future optimization.

------------------------------------------------------------------------

## 18. Reports and Exports

The application includes PDF and Excel export functionality for
operational reports.

Maintenance considerations:

-   Verify generated files after schema changes.
-   Preserve readable column widths in Excel.
-   Test merged-cell formatting carefully.
-   Verify date filtering.
-   Verify manual substitutes and unavailable substitutions render
    correctly.
-   Test reports with no data and large datasets.

------------------------------------------------------------------------

## 19. User Interface

The application uses standalone HTML templates rather than a shared
`base.html` at the current stage.

Recent UI work includes:

-   Login design.
-   Animated/colour-changing backgrounds.
-   Password show/hide controls.
-   Dashboard cards.
-   Search fields.
-   Back/home navigation.
-   Teacher timetable editing.
-   Free/occupied-period visual distinction.
-   Transparent school logo asset.

### Future recommendation

Introduce a shared `base.html` only after the current system is stable.
This would reduce duplicated CSS, navigation, footer, and background
code.

Do not perform this refactor immediately before production deployment
without regression testing.

------------------------------------------------------------------------

## 20. Application Routes

The current `app.py` contains approximately **30 Flask routes**.

Detected route function names include:

``` text
- home
- suggest_substitutions
- preview_substitutions
- finalize_substitutions
- login_page
- change_admin_password
- logout
- export_substitutions_pdf
- export_substitutions_excel
- export_absences_pdf
- change_password
- change_staff_password
- previous_absences
- today_substitutions
- staff_password
- my_absences
- my_substitutions
- my_timetable
- teacher_dashboard
- previous_substitutions
- substitutions_page
- delete_absence_page
- record_absence_page
- absences_page
- add_teacher_page
- count_absent
- timetable_page
- edit_teacher_page
- delete_teacher_page
- teachers_page
```

Developers should review route authorization whenever adding or changing
endpoints.

------------------------------------------------------------------------

## 21. Database Functions

The current `database.py` contains approximately **64 function
definitions**.

Detected functions include:

``` text
- connect_db
- create_database
- initialize_database
- load_substitution_cache
- update_teacher_full
- has_three_consecutive_periods_cached
- can_teacher_handle_class
- update_teacher_classes
- get_teacher_classes
- get_all_classes
- update_user_password
- add_teacher_classes
- get_absences_by_date
- get_all_substitutions_report
- get_all_absences_report
- update_admin_password
- update_staff_password
- get_staff_password
- login_user
- get_teacher_details
- count_absent_teachers
- search_absences
- count_substitutions
- count_absences_today
- count_substitutions_today_dashboard
- count_unavailable_substitutions
- get_dashboard_stats
- search_teachers
- fetch_substitutions_by_date
- count_teachers
- get_today_substitutions
- get_my_absences
- get_my_substitutions
- get_teacher_full_timetable
- count_free_periods
- has_three_consecutive_periods
- count_substitutions_today
- is_teacher_absent
- get_teacher_timetable_for_day
- insert_substitutions_batch
- insert_substitution
- is_teacher_already_assigned
- is_teacher_free
- absence_exists
- get_teacher_id
- delete_absence
- fetch_absences
- update_timetable
- update_teacher
- get_teacher
- update_timetable_day
- get_full_timetable
- get_teacher_timetable
- delete_teacher
- fetch_all_teachers
- get_teacher_names
- get_all_teacher_ids
- search_substitutions
- record_absence
- get_teacher_name
- fetch_substitutions
- add_teacher
- generate_substitution_candidates
```

The file is large and contains multiple functional domains.

### Future modularization

After deployment stability is achieved, consider splitting it into
modules such as:

``` text
database/
    connection.py
    teachers.py
    timetables.py
    absences.py
    substitutions.py
    users.py
    dashboard.py
    reports.py
```

Do not perform this solely for aesthetics. Refactor with tests and
incremental commits.

------------------------------------------------------------------------

## 22. Deployment and Cloudflare Tunnel

The application has been run locally and exposed remotely through
Cloudflare Tunnel.

### Relevant operational lessons

-   A Cloudflare 530/origin error may indicate tunnel/origin
    registration or connectivity problems rather than Flask logic.
-   Always test locally first.
-   Start the Flask application using the Python interpreter, for
    example:

``` text
python app.py
```

### VS Code warning

Do not use the generic Code Runner action for the Flask project.

During development, Code Runner created:

``` text
tempCodeRunnerFile.py
```

and executed selected snippets outside the application context, causing
misleading `NameError` failures.

Use the terminal or the Python extension's proper file execution
workflow.

------------------------------------------------------------------------

## 23. MySQL Backup Procedure

Before major code/database changes, create a database backup.

In MySQL Workbench:

``` text
Server
  -> Data Export
  -> Select alpha_substitution schema
  -> Select all required tables
  -> Export to Self-Contained File
  -> Dump Structure and Data
  -> Include Create Schema
  -> Start Export
```

Recommended naming:

``` text
Alpha_Substitution_Backup_YYYY-MM-DD.sql
```

Store the SQL backup separately from the application source backup.

------------------------------------------------------------------------

## 24. MySQL Restore Procedure

In MySQL Workbench:

``` text
Server
  -> Data Import
  -> Import from Self-Contained File
  -> Select SQL backup
  -> Choose/create target schema as required
  -> Start Import
```

After restoration:

1.  Verify table creation.
2.  Verify teacher count.
3.  Verify timetable data.
4.  Verify teacher-class mappings.
5.  Verify users.
6.  Test login.
7.  Test absence/candidate/finalization workflow.

------------------------------------------------------------------------

## 25. Source Backup Procedure

Maintain backups of:

``` text
Application project ZIP
Database SQL dump
Documentation/handoff file
Deployment configuration notes
```

Recommended release bundle:

``` text
Alpha_Substitution_System/
    source/
    database_backup/
    documentation/
```

Never treat the source ZIP as a replacement for the SQL database backup.

------------------------------------------------------------------------

## 26. Testing Checklist

### Authentication

-   Admin login succeeds.
-   Invalid admin login fails safely.
-   Teacher login succeeds.
-   Logout clears session.
-   Back navigation after logout does not expose protected pages.
-   Password changes persist.

### Teacher management

-   Add teacher.
-   Duplicate handling.
-   Search by full/partial name.
-   Edit teacher details.
-   Edit capable classes.
-   Edit all five timetable days.
-   Verify combined transaction persists all changes.
-   Verify rollback behavior on simulated failure.

### Absences

-   Record one absence.
-   Record multiple absences.
-   Prevent duplicate absence.
-   Verify date/day handling.
-   Verify dashboard absence count.

### Candidate generation

-   Absent teacher excluded.
-   Other absent teachers excluded.
-   Incapable teachers excluded.
-   Busy teachers excluded.
-   Already-assigned teachers excluded.
-   Free eligible teachers included.
-   Daily substitution warning works.
-   Continuous-period warning works.
-   Candidate sorting is correct.
-   Multiple absent teachers perform acceptably.

### Preview and finalization

-   Select registered teacher.
-   Enter manual substitute name.
-   Select Substitute Not Available.
-   Finalize one record.
-   Finalize 10+ records.
-   Verify batch transaction.
-   Verify records in database.

### Dashboard

-   Teacher count correct.
-   Absence count correct.
-   Substitution count correct.
-   Manual substitute not counted unavailable.
-   Explicit unavailable record counted unavailable.

### Teacher portal

-   Teacher sees appropriate timetable.
-   Teacher sees correct substitutions.
-   Teacher cannot access admin-only routes.
-   Password change works.

### Reports

-   PDF export.
-   Excel export.
-   Empty report.
-   Multi-record report.
-   Manual substitute display.
-   Unavailable substitute display.

### Performance

-   Home page load.
-   Candidate generation.
-   Finalization.
-   Teacher edit save.
-   Repeated refreshes.
-   Multiple browser tabs.

------------------------------------------------------------------------

## 27. Edge-Case Testing

Test deliberately difficult scenarios:

-   No capable substitute exists.
-   All capable teachers are absent.
-   All capable teachers are busy.
-   Candidate reaches maximum daily substitutions.
-   Candidate would exceed continuous-period rule.
-   Multiple teachers absent from the same class/period context.
-   Empty manual substitute input.
-   Very long manual substitute name.
-   Weekend/non-working date.
-   Repeated Submit clicks.
-   Repeated Finalize clicks.
-   Browser refresh on preview.
-   Session expiry during workflow.
-   MySQL failure before commit.
-   MySQL failure during batch insert.

------------------------------------------------------------------------

## 28. Known Technical Debt

### Large `database.py`

The database layer has grown substantially and should eventually be
modularized.

### Repeated connection patterns

Some functions may still independently open connections. Optimize only
when profiling demonstrates meaningful delay or when functions are
called inside loops.

### Duplicate or legacy functions

Historical development may have left functions that overlap with newer
optimized paths. Do not delete them without searching all call sites.

### Standalone templates

Shared page structure is duplicated. A future `base.html` refactor would
improve maintainability.

### Automated testing

The project currently benefits heavily from manual system/UAT testing.
Automated tests should be added for critical scheduling rules and
transaction behavior.

------------------------------------------------------------------------

## 29. Security Recommendations Before Wider Deployment

-   Do not hard-code production database passwords in source control.
-   Use environment variables for secrets.
-   Use a strong Flask secret key from configuration/environment.
-   Review default teacher passwords.
-   Require password changes where appropriate.
-   Use secure cookie settings for public HTTPS deployment.
-   Verify CSRF protection for state-changing forms.
-   Validate all user inputs.
-   Keep MySQL inaccessible directly from the public internet.
-   Keep Python packages updated.
-   Restrict administrator routes by role.
-   Add application logging without logging passwords or secrets.
-   Back up the database regularly.

------------------------------------------------------------------------

## 30. Recommended Database Index Review

As data grows, review indexes for columns frequently used in filtering
and joins, including:

``` text
absences.teacher_id
absences.date
timetable.teacher_id
timetable.day
teacher_classes.teacher_id
teacher_classes.class_name
substitutions.absence_id
substitutions.substitute_teacher_id
substitutions.period
```

Before adding indexes, inspect existing primary keys, unique
constraints, and indexes to avoid unnecessary duplication.

------------------------------------------------------------------------

## 31. Recommended Future Roadmap

### Phase 1 --- Stabilization

-   Complete UAT.
-   Fix logical bugs.
-   Verify every write path commits.
-   Verify rollback paths.
-   Create production backup.

### Phase 2 --- Deployment hardening

-   Environment-based secrets.
-   Production WSGI server.
-   Logging.
-   Error pages.
-   CSRF protection.
-   Backup schedule.
-   Deployment documentation.

### Phase 3 --- Maintainability

-   Introduce `base.html`.
-   Split `database.py`.
-   Remove verified dead/duplicate code.
-   Add service/domain layer if useful.
-   Standardize database transaction handling.

### Phase 4 --- Automated quality

-   Unit tests for candidate rules.
-   Integration tests for MySQL operations.
-   Route authorization tests.
-   Transaction rollback tests.
-   Performance regression tests.

### Phase 5 --- Optional product improvements

-   Audit log.
-   Administrative activity history.
-   Better analytics.
-   Notification features.
-   Improved responsive/mobile UI.
-   More detailed substitution workload reports.

------------------------------------------------------------------------

## 32. Troubleshooting Guide

### `tempCodeRunnerFile.py` appears

Cause: VS Code Code Runner is executing a temporary snippet.

Fix:

``` text
Run with: python app.py
```

### MySQL InterfaceError / lost connection

Check:

-   MySQL service status.
-   Workbench connectivity.
-   Repeated connection creation.
-   Unclosed cursors/connections.
-   Correct connection configuration.

### Candidate generation is slow

Profile:

``` text
absence query
cache loading
candidate processing
total time
```

Never assume Python loops are the bottleneck. During this project,
candidate processing dropped to \~0.001 seconds after caching.

### Finalize is slow

Check whether insertion is performed one connection per record. Prefer
batch insertion and one transaction.

### Home page is slow

Check whether each dashboard statistic opens a separate connection.
Prefer consolidated statistics loading.

### Edit Teacher save is slow

Use the combined transaction rather than separate update connections.

### Manual substitute counted unavailable

Unavailable logic must check both teacher ID and manual substitute name.

------------------------------------------------------------------------

## 33. Developer Maintenance Rules

When modifying this system:

1.  Back up source and database first.
2.  Change one subsystem at a time.
3.  Test locally before testing through Cloudflare.
4.  Profile before optimizing.
5.  Never open database connections inside large nested loops if data
    can be loaded once.
6.  Prefer batch operations.
7.  Use transactions for logically related writes.
8.  Roll back on failure.
9.  Keep candidate preview separate from final persistence.
10. Test manual substitute and unavailable states separately.
11. Verify role authorization.
12. Update this handoff after major architectural changes.

------------------------------------------------------------------------

## 34. Final Current-State Summary

The Alpha Substitution Management System is a functional Flask/MySQL
school scheduling application with approximately 90 teachers, timetable
management, absence recording, candidate generation, VP
review/finalization, manual substitute handling, dashboards, teacher
access, reporting, and deployment support.

The most significant recent improvement was the redesign of database
interaction patterns. Repeated MySQL connections caused severe delays
and timeouts. Cache-based candidate processing, batch finalization,
consolidated dashboard statistics, explicit transactions, and combined
teacher updates produced substantial performance improvements.

The immediate priority is **system testing and logical correctness**,
not large-scale refactoring. Once UAT is complete and the system is
stable, the recommended next steps are deployment hardening, automated
tests, modularization, and improved operational documentation.

------------------------------------------------------------------------

## 35. Handoff Checklist

Before transferring the project:

-   [ ] Latest source ZIP included.
-   [ ] Latest SQL dump included.
-   [ ] This handoff document included.
-   [ ] Database credentials transferred securely and separately.
-   [ ] Flask secret/configuration documented securely.
-   [ ] Admin login tested.
-   [ ] Teacher login tested.
-   [ ] One complete absence-to-finalization workflow tested.
-   [ ] Manual substitute tested.
-   [ ] Substitute Not Available tested.
-   [ ] Dashboard counts verified.
-   [ ] PDF/Excel exports verified.
-   [ ] Local startup procedure verified.
-   [ ] Cloudflare/deployment procedure verified.
-   [ ] Recovery from SQL backup tested or documented.

------------------------------------------------------------------------

## 36. Recent Changes — 10 July 2026

The system now includes subject-aware combined-class substitution handling. Language teachers with entries such as `X` or `X-C+D` generate one substitution requirement with grade-based candidate eligibility. Non-Language teachers with combined sections generate separate section-specific substitutions while retaining normal eligibility and availability rules.

The manual substitute interface now uses a custom searchable suggestion list showing only teachers who are free for the relevant period, not absent, not the absent teacher, and not already assigned during that period. Custom manual names remain supported.

Frontend and backend validation prevent the same teacher from being assigned to multiple classes during the same period. Frontend JavaScript displays a warning and disables Preview; backend validation remains authoritative.

Mr. Gowtham is excluded from automatic and manual substitution candidate lists on Tuesdays only, despite his Tuesday timetable being stored as `Free`. He is processed normally on other weekdays.

Upcoming Absences now supports deletion through the existing delete workflow. Today's Absences displays an empty-state message when no records exist. Teacher tables use sequential visible numbering and the Teachers page supports live name filtering while typing.

Pages use the standardized header `ALPHA SCHOOL, CIT NAGAR` followed by `SUBSTITUTION MANAGEMENT SYSTEM`.

Today's Substitutions PDF export now filters only today's records, displays the date in `DD-MM-YYYY` format, uses A4 landscape orientation, centers both headings, places the date above the table, and uses the columns `Period | Absent Teacher | Class | Substitute Teacher`. Registered substitutes, manual substitutes, and unavailable substitutions are handled separately.

A MySQL startup compatibility issue involving `caching_sha2_password` was addressed by verifying/upgrading `mysql-connector-python` in the Python environment running `app.py`.

### Additional Regression Tests

- Verify Language combined classes generate one substitution requirement.
- Verify non-Language combined sections generate separate substitutions.
- Verify grade-based Language eligibility and section-specific non-Language eligibility.
- Verify manual suggestions contain only free and available teachers.
- Verify custom manual names remain possible.
- Verify duplicate same-period assignments are blocked in frontend and backend.
- Verify Mr. Gowtham is excluded on Tuesday only.
- Verify upcoming absence deletion and Today's Absences empty state.
- Verify live teacher filtering.
- Verify Today's PDF contains only today's records, uses `DD-MM-YYYY`, and renders in A4 landscape.

------------------------------------------------------------------------

**End of Developer Handoff**
