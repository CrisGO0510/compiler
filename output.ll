target triple = "x86_64-pc-linux-gnu"
define dso_local noundef i32 @main() {
entry:
define dso_local noundef i32 @square(i32 noundef %num) {
entry:
  %num.addr = alloca i32, align 4
  store i32 %num, ptr %num.addr, align 4
  %0 = load i32, ptr %num.addr, align 4
  %1 = mul nsw i32 %0, %0
  ret i32 %1
}
  %call = call noundef i32 @square(i32 noundef 2)
  ret i32 %call
  ret i32 0
}
