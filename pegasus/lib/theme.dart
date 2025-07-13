import 'package:flutter/material.dart';

class PegasusTheme {
  static const Color primaryColor = Colors.indigo;
  static const MaterialColor primarySwatch = Colors.indigo;
}

final ThemeData appTheme = ThemeData(
  primarySwatch: PegasusTheme.primarySwatch,
  brightness: Brightness.light,
);


final ThemeData darkAppTheme = ThemeData(
  primarySwatch: PegasusTheme.primarySwatch,
  brightness: Brightness.dark,
);