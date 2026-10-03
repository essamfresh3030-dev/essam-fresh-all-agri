import 'package:path/path.dart';
import 'package:sqflite/sqflite.dart';

class LocalDb {
  static final LocalDb instance = LocalDb._();
  LocalDb._();
  Database? _db;

  Future<Database> get db async {
    if (_db != null) return _db!;
    final p = join(await getDatabasesPath(), 'agri_erp.db');
    _db = await openDatabase(p, version: 2, onCreate: (db, _) async => _create(db), onUpgrade: (db, old, _) async { if (old < 2) await _create(db); });
    return _db!;
  }

  Future<void> _create(Database db) async {
    await db.execute('''CREATE TABLE IF NOT EXISTS sync_queue(
      id TEXT PRIMARY KEY, endpoint TEXT NOT NULL, method TEXT NOT NULL,
      payload TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL)''');
    await db.execute('''CREATE TABLE IF NOT EXISTS cache(
      key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)''');
  }

  Future<void> enqueue(String id, String endpoint, String method, String payload) async {
    await (await db).insert('sync_queue', {'id': id, 'endpoint': endpoint, 'method': method, 'payload': payload, 'status': 'PENDING', 'attempts': 0, 'created_at': DateTime.now().toIso8601String()});
  }

  Future<List<Map<String,Object?>>> pending() async => (await db).query('sync_queue', where: 'status = ?', whereArgs: ['PENDING'], orderBy: 'created_at');

  Future<void> markSynced(String id) async => (await db).update('sync_queue', {'status':'SYNCED'}, where:'id=?', whereArgs:[id]);
  Future<void> markFailed(String id) async => (await db).update('sync_queue', {'status':'PENDING','attempts':1}, where:'id=?', whereArgs:[id]);

  Future<int> pendingCount() async => Sqflite.firstIntValue(await (await db).rawQuery("SELECT COUNT(*) FROM sync_queue WHERE status='PENDING'")) ?? 0;
}
