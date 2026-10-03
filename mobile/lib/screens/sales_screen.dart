import 'package:flutter/material.dart';
import '../services/api_client.dart';

class SalesScreen extends StatefulWidget {
  final ApiClient api;
  const SalesScreen({super.key, required this.api});
  @override State<SalesScreen> createState() => _SalesScreenState();
}

class _SalesScreenState extends State<SalesScreen> {
  List<dynamic> orders = [];
  List<dynamic> customers = [];
  bool loading = true;

  @override void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => loading = true);
    final o = await widget.api.getList('sales/orders');
    final c = await widget.api.getList('customers');
    if (mounted) setState(() { orders = o; customers = c; loading = false; });
  }

  void _createOrder() {
    final custCtrl = TextEditingController();
    final channelVal = ValueNotifier<String>('LOCAL');
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => Padding(
        padding: EdgeInsets.only(left: 16, right: 16, top: 16, bottom: MediaQuery.of(context).viewInsets.bottom + 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('امر بيع جديد', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: customers.isNotEmpty ? customers.first['id'] : null,
              decoration: const InputDecoration(labelText: 'العميل'),
              items: customers.map((c) => DropdownMenuItem(value: c['id'].toString(), child: Text(c['name'] ?? 'عميل'))).toList(),
              onChanged: (v) => custCtrl.text = v ?? '',
            ),
            const SizedBox(height: 12),
            ValueListenableBuilder<String>(
              valueListenable: channelVal,
              builder: (context, val, _) => DropdownButtonFormField<String>(
                value: val,
                decoration: const InputDecoration(labelText: 'قناة البيع'),
                items: const [
                  DropdownMenuItem(value: 'LOCAL', child: Text('محلي (بدون VAT)')),
                  DropdownMenuItem(value: 'EXPORT', child: Text('تصدير')),
                ],
                onChanged: (v) => channelVal.value = v ?? 'LOCAL',
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () async {
                final custId = custCtrl.text.isNotEmpty ? custCtrl.text : (customers.isNotEmpty ? customers.first['id'] : '');
                if (custId.isEmpty) return;
                final ok = await widget.api.post('sales/orders', {
                  'customer_id': custId,
                  'channel': channelVal.value,
                  'order_date': DateTime.now().toIso8601String().substring(0, 10),
                  'currency': channelVal.value == 'EXPORT' ? 'USD' : 'EGP',
                  'exchange_rate': 1,
                });
                if (mounted) {
                  Navigator.pop(context);
                  _load();
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ok ? 'تم إضافة أمر البيع' : 'حدث خطأ')));
                }
              },
              child: const Text('حفظ'),
            )
          ],
        ),
      ),
    );
  }

  @override Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('إدارة المبيعات والتصدير'), actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh))]),
      body: loading ? const Center(child: CircularProgressIndicator()) : ListView.builder(
        itemCount: orders.length,
        itemBuilder: (_, i) {
          final o = orders[i];
          return Card(
            margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            child: ListTile(
              leading: Icon(o['channel'] == 'EXPORT' ? Icons.flight_takeoff : Icons.store, color: Colors.green),
              title: Text('امر بيع: ${o['id'].toString().substring(0, 8)}'),
              subtitle: Text('القناة: ${o['channel']} | الحالة: ${o['status'] ?? 'DRAFT'}'),
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _createOrder,
        child: const Icon(Icons.add),
      ),
    );
  }
}
