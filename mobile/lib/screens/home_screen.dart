import 'package:flutter/material.dart';
import '../services/api_client.dart';

class HomeScreen extends StatelessWidget {
  final ApiClient api;

  const HomeScreen({super.key, required this.api});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Agri ERP - الرئيسية'),
      ),
      body: GridView.count(
        crossAxisCount: 2,
        padding: const EdgeInsets.all(16),
        children: [
          _buildMenuCard(context, 'المشتريات', Icons.shopping_cart, '/procurement'),
          _buildMenuCard(context, 'المبيعات', Icons.sell, '/sales'),
          _buildMenuCard(context, 'الحسابات', Icons.account_balance, '/accounting'),
          _buildMenuCard(context, 'الموارد البشرية', Icons.people, '/hr'),
          _buildMenuCard(context, 'التقارير', Icons.bar_chart, '/reports'),
        ],
      ),
    );
  }

  Widget _buildMenuCard(BuildContext context, String title, IconData icon, String route) {
    return Card(
      child: InkWell(
        onTap: () {
          if (ModalRoute.of(context)?.settings.name != route) {
            Navigator.pushNamed(context, route);
          }
        },
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 48),
            const SizedBox(height: 8),
            Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }
}

class SimpleModule extends StatelessWidget {
  final String title;
  final IconData icon;

  const SimpleModule({super.key, required this.title, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 72),
            const SizedBox(height: 16),
            Text('واجهة $title قيد التوسعة في الإصدار التالي.'),
            const SizedBox(height: 8),
            const Text('الـAPI الأساسي جاهز للعمل.'),
          ],
        ),
      ),
    );
  }
}
