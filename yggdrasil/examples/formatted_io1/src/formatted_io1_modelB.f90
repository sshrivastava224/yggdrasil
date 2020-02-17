program main
  ! Include methods for input/output channels
  use fygg

  ! Declare resulting variables and create buffer for received message
  integer, parameter :: mybufsiz = 1000
  integer :: flag = 1
  type(yggcomm) :: in_channel, out_channel
  character(len=100), target :: msg = "hello"
  integer(kind=c_size_t), target :: msg_siz = 100

  ! Initialize input/output channels
  in_channel = ygg_input("inputB")
  out_channel = ygg_output("outputB")

  ! Loop until there is no longer input or the queues are closed
  do while (flag.ge.0)

     ! Receive input from input channel
     ! If there is an error, the flag will be negative
     ! Otherwise, it is the number of variables filled
     flag = ygg_recv_var_realloc(in_channel, &
          [yggarg(msg), yggarg(msg_siz)])
     if (flag.lt.0) then
        print *, "Model B: No more input."
        exit
     end if

     ! Print received message
     print *, "Model B: ", msg

     ! Send output to output channel
     ! If there is an error, the flag will be negative
     flag = ygg_send_var(out_channel, &
          [yggarg(msg), yggarg(msg_siz)])
     if (flag.lt.0) then
        print *, "Model B: Error sending output."
        exit
     end if

  end do

  call exit(0)

end program main
