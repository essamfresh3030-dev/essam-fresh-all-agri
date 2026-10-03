import 'package:flutter/material.dart';
import '../services/api_client.dart';

class OperationFormScreen extends StatefulWidget {
  final ApiClient api;
  const OperationFormScreen({super.key, required this.api});
  @override State<OperationFormScreen> createState() => _OperationFormScreenState();
}

class _OperationFormScreenState extends State<OperationFormScreen> {
  final amount = TextEditingController();
  final quantity = TextEditingController();
  final unit = TextEditingController();
  final workers = TextEditingController();
  final description = TextEditingController();
  List<dynamic> cycles = [];
  String? cycleId;
  String type = 'IRRIGATION';
  bool busy = false;
  final types = const {
    'IRRIGATION':'ري', 'FERTILIZATION':'تسميد', 'PESTICIDE':'مبيدات',
    'LABOR':'عمالة', 'HARVEST':'حصاد', 'WASTE':'هالك', 'OTHER':'أخرى'
  };

  @override void initState(){ super.initState(); _load(); }
  Future<void> _load() async { final x=await widget.api.getList('crop-cycles'); if(mounted)setState(()=>cycles=x); }
  Future<void> save() async {
    if(cycleId==null){_msg('اختر دورة المحصول');return;}
    setState(()=>busy=true);
    final ok=await widget.api.postOfflineSafe('farm-operations', {
      'crop_cycle_id':cycleId, 'operation_type':type,
      'operation_date':DateTime.now().toIso8601String().substring(0,10),
      'quantity':double.tryParse(quantity.text), 'unit':unit.text.trim().isEmpty?null:unit.text.trim(),
      'amount':double.tryParse(amount.text)??0, 'description':description.text.trim().isEmpty?null:description.text.trim(),
      'worker_count':int.tryParse(workers.text),
    });
    if(!mounted)return; setState(()=>busy=false);
    _msg(ok?'تم تسجيل العملية':'تم حفظها محلياً وستتم مزامنتها عند الاتصال');
    if(ok) Navigator.pop(context,true);
  }
  void _msg(String x)=>ScaffoldMessenger.of(context).showSnackBar(SnackBar(content:Text(x)));
  @override Widget build(BuildContext c)=>Scaffold(appBar:AppBar(title:const Text('تسجيل عملية زراعية')),body:ListView(padding:const EdgeInsets.all(16),children:[
    DropdownButtonFormField<String>(value:cycleId,decoration:const InputDecoration(labelText:'دورة المحصول'),items:cycles.map((x)=>DropdownMenuItem(value:x['id'] as String,child:Text('${x['id'].toString().substring(0,8)} — ${x['status']??''}'))).toList(),onChanged:(v)=>setState(()=>cycleId=v)),
    const SizedBox(height:12), DropdownButtonFormField<String>(value:type,decoration:const InputDecoration(labelText:'نوع العملية'),items:types.entries.map((e)=>DropdownMenuItem(value:e.key,child:Text(e.value))).toList(),onChanged:(v)=>setState(()=>type=v!)),
    const SizedBox(height:12), Row(children:[Expanded(child:TextField(controller:amount,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'التكلفة'))),const SizedBox(width:10),Expanded(child:TextField(controller:quantity,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'الكمية')))]),
    const SizedBox(height:12), Row(children:[Expanded(child:TextField(controller:unit,decoration:const InputDecoration(labelText:'الوحدة'))),const SizedBox(width:10),Expanded(child:TextField(controller:workers,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'عدد العمال')))]),
    const SizedBox(height:12), TextField(controller:description,maxLines:3,decoration:const InputDecoration(labelText:'الوصف / الملاحظات',border:OutlineInputBorder())),
    const SizedBox(height:20), FilledButton.icon(onPressed:busy?null:save,icon:const Icon(Icons.save),label:Text(busy?'جاري الحفظ...':'حفظ العملية')),
  ]));
}
