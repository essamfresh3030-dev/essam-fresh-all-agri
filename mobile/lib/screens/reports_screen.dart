import 'package:flutter/material.dart';
import '../services/api_client.dart';

class ReportsScreen extends StatefulWidget {
  final ApiClient api;
  const ReportsScreen({super.key, required this.api});
  @override State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  Map<String, dynamic>? kpis;
  bool loading = true;

  @override void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => loading = true);
    final res = await widget.api.getObject('dashboard/kpis');
    if (mounted) setState(() { kpis = res; loading = false; });
  }

  @override Widget build(BuildContext context) {
    final k = kpis ?? {};
    return Scaffold(
      appBar: AppBar(title: const Text('التقارير ولوحة الربحية')),
      body: loading ? const Center(child: CircularProgressIndicator()) : RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _kpiCard('إجمالي المبيعات (EGP)', '${k['revenue_egp'] ?? 0}'),
            _kpiCard('تكلفة الإنتاج والمنتج (EGP)', '${k['product_cost_egp'] ?? 0}'),
            _kpiCard('تكلفة الخدمات والمحاصيل (EGP)', '${k['crop_cost_egp'] ?? 0}'),
            _kpiCard('صافي الربح (EGP)', '${k['profit_egp'] ?? 0}', isProfit: true),
            _kpiCard('نسبة الهامش %', '${k['margin_percent'] ?? 0}%'),
          ],
        ),
      ),
    );
  }

  Widget _kpiCard(String title, String val, {bool isProfit = false}) {
    return Card(
      color: isProfit ? Colors.green[50] : null,
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            Text(val, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: isProfit ? Colors.green[800] : Colors.black800)),
          ],
        ),
      ),
    );
  }
}
