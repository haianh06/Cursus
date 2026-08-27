# CPU Datapath basics

## Thành phần
- Register file
- ALU
- PC / IR
- Memory data/address ports
- Multiplexers chọn nguồn dữ liệu

## Trace một lệnh R-type
1. Instruction fetch (PC → memory)
2. Decode + đọc register rs/rt
3. ALU thực hiện phép toán
4. Ghi kết quả vào rd (RegWrite=1)

## Self-study
Hoàn thành worksheet control signals cho load/store và branch.
