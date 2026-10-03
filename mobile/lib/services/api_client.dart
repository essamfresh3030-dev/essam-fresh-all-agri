import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:uuid/uuid.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'local_db.dart';

class ApiClient {
  final String baseUrl;
  final LocalDb localDb;
  ApiClient({required this.baseUrl, LocalDb? localDb}) : localDb = localDb ?? LocalDb.instance;

  Future<Map<String,String>> _headers() async {
    final p=await SharedPreferences.getInstance();
    final token=p.getString('access_token');
    return {'content-type':'application/json', if(token!=null) 'Authorization':'Bearer $token'};
  }
  Future<bool> login(String username,String password) async {
    try { final r=await http.post(Uri.parse('$baseUrl/api/auth/login'),headers:{'content-type':'application/json'},body:jsonEncode({'username':username,'password':password})).timeout(const Duration(seconds:8));
      if(r.statusCode==200){ final p=await SharedPreferences.getInstance(); await p.setString('access_token',(jsonDecode(r.body) as Map)['access_token']); return true; }
    } catch(_){ }
    return false;
  }
  Future<void> logout() async { final p=await SharedPreferences.getInstance(); await p.remove('access_token'); }
  Future<bool> isLoggedIn() async => (await SharedPreferences.getInstance()).getString('access_token')!=null;
  Future<bool> health() async { try { final r=await http.get(Uri.parse('$baseUrl/health')).timeout(const Duration(seconds:5)); return r.statusCode==200; } catch(_){ return false; } }
  Future<List<dynamic>> getList(String endpoint) async { try { final r=await http.get(Uri.parse('$baseUrl/api/$endpoint'),headers:await _headers()).timeout(const Duration(seconds:8)); if(r.statusCode>=200&&r.statusCode<300)return jsonDecode(r.body) as List<dynamic>; }catch(_){} return []; }
  Future<bool> post(String endpoint,Map<String,dynamic> body) async { try { final r=await http.post(Uri.parse('$baseUrl/api/$endpoint'),headers:await _headers(),body:jsonEncode(body)).timeout(const Duration(seconds:10)); return r.statusCode>=200&&r.statusCode<300; } catch(_){ return false; } }
  Future<Map<String,dynamic>?> getObject(String endpoint) async { try { final r=await http.get(Uri.parse('$baseUrl/api/$endpoint'),headers:await _headers()).timeout(const Duration(seconds:8)); if(r.statusCode>=200&&r.statusCode<300)return jsonDecode(r.body) as Map<String,dynamic>; }catch(_){} return null; }
  Future<bool> postOfflineSafe(String endpoint,Map<String,dynamic> body) async { final payload=jsonEncode(body); try { final r=await http.post(Uri.parse('$baseUrl/api/$endpoint'),headers:await _headers(),body:payload).timeout(const Duration(seconds:8)); if(r.statusCode>=200&&r.statusCode<300)return true; }catch(_){} await localDb.enqueue(const Uuid().v4(),'/api/$endpoint','POST',payload); return false; }
  Future<int> syncPending() async { final rows=await localDb.pending(); if(rows.isEmpty)return 0; final ops=rows.map((r)=>{'client_operation_id':r['id'],'endpoint':r['endpoint'],'method':r['method'],'payload':jsonDecode(r['payload'] as String)}).toList(); try { final r=await http.post(Uri.parse('$baseUrl/api/sync/batch'),headers:await _headers(),body:jsonEncode({'operations':ops})).timeout(const Duration(seconds:15)); if(r.statusCode==200){final results=(jsonDecode(r.body)['results'] as List); for(final x in results){if(x['status']=='SYNCED') await localDb.markSynced(x['client_operation_id']);} return results.where((x)=>x['status']=='SYNCED').length;} }catch(_){} return 0; }
}
