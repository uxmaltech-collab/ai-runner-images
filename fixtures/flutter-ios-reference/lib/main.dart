import 'package:flutter/material.dart';

void main() => runApp(const HelloWorldApp());

class HelloWorldApp extends StatefulWidget {
  const HelloWorldApp({super.key});
  @override
  State<HelloWorldApp> createState() => _HelloWorldAppState();
}

class _HelloWorldAppState extends State<HelloWorldApp> {
  int count = 0;
  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    home: Scaffold(
      appBar: AppBar(title: const Text('Runner image validation')),
      body: Center(child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Semantics(identifier: 'hello-title', child: const Text('Hello World')),
          Semantics(identifier: 'hello-count', child: Text('Count: $count')),
          Semantics(identifier: 'hello-increment', child: ElevatedButton(
            onPressed: () => setState(() => count++),
            child: const Text('Increment'),
          )),
        ],
      )),
    ),
  );
}
