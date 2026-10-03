import 'package:flutter/material.dart';
import '../services/api_client.dart';

class HRScreen extends StatefulWidget {
  final ApiClient api;
  const HRScreen({super.key, required this.api});
  @override State<HRScreen> createState() => _HRScreenState();
}

class _HRScreenState extends State<HRScreen> {
  List<dynamic> employees = [];
  bool loading = true;

  @override void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => loading = true);
    final emp = await widget.api.getList('employees');
    if (mounted) setState(() { employees = emp; loading = false; });
  }

  void _addEmployee() {
    final codeCtrl = TextEditingController();
    final nameCtrl = TextEditingController();
    final jobCtrl = TextEditingController();

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => Padding(
        padding: EdgeInsets.only(left: 16, right: 16, top: 16, bottom: MediaQuery.of(context).viewInsets.bottom + 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('إضافة موظف جديد', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            TextField(controller: codeCtrl, decoration: const InputDecoration(labelText: 'كود الموظف')),
            TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'الاسم الكامل')),
            TextField(controller: jobCtrl, decoration: const InputDecoration(labelText: 'المسمى الوظيفي')),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () async {
                if (codeCtrl.text.isEmpty || nameCtrl.text.isEmpty) return;
                final ok = await widget.api.post('employees', {
                  'employee_code': codeCtrl.text,
                  'full_name': nameCtrl.text,
                  'job_title': jobCtrl.text,
                  'salary': 0,
                });
                if (mounted) {
                  Navigator.pop(context);
                  _load();
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
      appBar: AppBar(title: const Text('الموارد البشرية والحضور')),
      body: loading ? const Center(child: CircularProgressIndicator()) : ListView.builder(
        itemCount: employees.length,
        itemBuilder: (_, i) {
          final e = employees[i];
          return Card(
            child: ListTile(
              leading: const Icon(Icons.badge, color: Colors.orange),
              title: Text('${e['employee_code']} - ${e['full_name']}'),
              subtitle: Text('الوظيفة: ${e['job_title'] ?? '-'}'),
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _addEmployee,
        child: const Icon(Icons.person_add),
      ),
    );
  }
}
