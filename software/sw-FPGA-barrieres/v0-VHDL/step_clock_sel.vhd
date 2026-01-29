library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity step_clock_sel is
  port (
    clk       : in  STD_LOGIC;                        -- 100 MHz
    reset     : in  STD_LOGIC;                        -- actif haut
    enable    : in  STD_LOGIC;
    speed_sel : in  STD_LOGIC_VECTOR(1 downto 0);     -- {SW3,SW2}
    step_ce   : out STD_LOGIC
  );
end step_clock_sel;

architecture Behavioral of step_clock_sel is
  constant N_100HZ : integer := 1_000_000;
  constant N_200HZ : integer :=   500_000;
  constant N_400HZ : integer :=   250_000;
  constant N_800HZ : integer :=   125_000;

  signal target_N : integer := N_100HZ;
  signal cnt      : integer := 0;
  signal ce_i     : std_logic := '0';
begin
  step_ce <= ce_i;

  process(speed_sel)
  begin
    case speed_sel is
      when "00"   => target_N <= N_100HZ;
      when "01"   => target_N <= N_200HZ;
      when "10"   => target_N <= N_400HZ;
      when others => target_N <= N_800HZ;
    end case;
  end process;

  process(clk)
  begin
    if rising_edge(clk) then
      ce_i <= '0';
      if reset='1' then
        cnt <= 0;
      elsif enable='1' then
        if cnt >= (target_N - 1) then
          cnt  <= 0;
          ce_i <= '1';
        else
          cnt <= cnt + 1;
        end if;
      else
        cnt <= 0;
      end if;
    end if;
  end process;
end Behavioral;
