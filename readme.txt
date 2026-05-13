
运行结果会放在：
E:\code\ZEROLET\data_c\

cd E:\code\ZEROLET

paper extremes
gcc -std=c11 -Wall -Wextra -O2 -DZEROLET_EVALUATION_NO_MAIN analysis_zero_let.c evaluation_zero_let.c extremes_zero_let.c -lm -o extremes_zero_let_c.exe
.\extremes_zero_let_c.exe
也可以手动指定参数：
.\extremes_zero_let_c.exe 2 12 3
指定随机种子：
.\extremes_zero_let_c.exe 2 12 3 12345

runtime
gcc -std=c11 -Wall -Wextra -O2 analysis_zero_let.c evaluation_zero_let.c -lm -o evaluation_zero_let_c.exe
.\evaluation_zero_let_c.exe
生成RoverC 和 runtime的结果图

也可以命令行传参：
.\evaluation_zero_let_c.exe 3 6 1

比如只跑 n=3：
.\evaluation_zero_let_c.exe 3 3 1