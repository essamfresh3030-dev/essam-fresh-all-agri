import 'package:flutter/material.dart';
import 'services/api_client.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';

void main() async { WidgetsFlutterBinding.ensureInitialized(); final api=ApiClient(baseUrl:const String.fromEnvironment('API_URL',defaultValue:'http://127.0.0.1:8000')); runApp(AgriERPApp(api:api)); }
class AgriERPApp extends StatelessWidget{final ApiClient api; const AgriERPApp({super.key,required this.api}); @override Widget build(BuildContext c)=>MaterialApp(debugShowCheckedModeBanner:false,title:'Agri ERP',theme:ThemeData(useMaterial3:true,colorSchemeSeed:Colors.green),home:FutureBuilder<bool>(future:api.isLoggedIn(),builder:(c,s)=>s.data==true?HomeScreen(api:api):LoginScreen(api:api)));}
