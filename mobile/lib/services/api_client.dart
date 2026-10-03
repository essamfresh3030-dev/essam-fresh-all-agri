import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import 'local_db.dart'; // تم إضافة الاستيراد لمنع خطأ Couldn't find constructor 'LocalDb'

class ApiClient {
  static const String defaultUrl = 'https://agri-erp-demo.onrender.com';
  String baseUrl;
  final LocalDb localDb = LocalDb();

  ApiClient({this.baseUrl = defaultUrl});

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    final savedUrl = prefs.getString('api_base_url');
    if (savedUrl != null && savedUrl.isNotEmpty) {
      baseUrl = savedUrl;
    }
  }

  Future<bool> isLoggedIn() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    return token != null && token.isNotEmpty;
  }

  Future<Map<String, String>> _headers() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  Future<dynamic> get(String endpoint) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/$endpoint'),
      headers: await _headers(),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('فشل جلب البيانات: ${response.statusCode}');
  }

  Future<bool> postOfflineSafe(String endpoint, Map<String, dynamic> body) async {
    final payload = jsonEncode(body);
    try {
      final r = await http.post(
        Uri.parse('$baseUrl/api/$endpoint'),
        headers: await _headers(),
        body: payload,
      ).timeout(const Duration(seconds: 8));
      if (r.statusCode >= 200 && r.statusCode < 300) return true;
    } catch (_) {}
    await localDb.enqueue(Uuid().v4(), '/api/$endpoint', 'POST', payload);
    return false;
  }
}
