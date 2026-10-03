import 'package:flutter/material.dart';
import 'services/api_client.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';
import 'screens/procurement_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final api = ApiClient(
    baseUrl: const String.fromEnvironment(
      'API_URL',
      defaultValue: 'https://agri-erp-demo.onrender.com',
    ),
  );
  await api.init();
  runApp(AgriERPApp(api: api));
}

class AgriERPApp extends StatelessWidget {
  final ApiClient api;
  const AgriERPApp({super.key, required this.api});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Agri ERP',
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: Colors.green,
      ),
      home: FutureBuilder<bool>(
        future: api.isLoggedIn(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            );
          }
          if (snapshot.data == true) {
            return HomeScreen(api: api);
          }
          return LoginScreen(api: api);
        },
      ),
      routes: {
        '/home': (context) => HomeScreen(api: api),
        '/login': (context) => LoginScreen(api: api),
        '/procurement': (context) => const ProcurementScreen(),
      },
    );
  }
}
