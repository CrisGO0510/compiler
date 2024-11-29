define dso_local i32 @constant(i32 noundef %2) #0 {
write:
	%3 = alloca i32, align 4
	store i32 %2, ptr %3, align 4
	%4 = load i32, ptr %3, align 4
	%5 = load i32, ptr %3, align 4
	%6 = add nsw i32 2, %5
	%7 = mul nsw i32 3, %6
	%8 = add nsw i32 %4, %7
	ret i32 %8
}
define dso_local i32 @main() #1 {
write:
	ret i32 %2
}
