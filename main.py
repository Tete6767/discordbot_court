import os
import discord
from discord import app_commands
from discord.ext import commands
from discord import ui
import datetime
from myserver import server_on

# --- ส่วนของ Flask Server (ทำให้บอทออนไลน์ 24 ชม.) ---
from flask import Flask
from threading import Thread


app = Flask('')

@app.route('/')
def home():
    return "บอทกำลังทำงานอยู่!"

def run():
    app.run(host='0.0.0.0', port=8080)

def server_on():
    t = Thread(target=run)
    t.start()

# --- ส่วนของ Discord Bot ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # รัน Flask Server ทันทีที่บอทเริ่มทำงาน
        server_on()
        print("✅ Flask server is online!")

bot = MyBot()

# ตัวนับลำดับห้อง (เบื้องต้นจะรีเซ็ตถ้าบอทดับ หากต้องการถาวรควรใช้ Database)
ticket_counter = 1

# --- หน้าต่างกรอกข้อมูล (Modal) สำหรับส่งฟ้อง ---
class FilingModal(ui.Modal, title='ศูนย์รับเรื่อง พระธรรมนูญ (ส่งฟ้อง)'):
    u_name = ui.TextInput(label='[ ชื่อบัญชีผู้ฟ้อง | Username ]', placeholder='ชื่อของคุณ...')
    u_rank = ui.TextInput(label='[ ยศผู้ฟ้อง | Rank ]', placeholder='ระบุยศของคุณ...')
    u_branch = ui.TextInput(label='[ สังกัดผู้ฟ้อง | Branch ]', placeholder='ระบุสังกัดของคุณ...')
    accused_info = ui.TextInput(label='[ ข้อมูลผู้กระทำผิด ]', placeholder='ชื่อ | ยศ | สังกัด ของผู้กระทำผิด', style=discord.TextStyle.paragraph)
    description = ui.TextInput(label='[ บรรยายเหตุการณ์ ]', style=discord.TextStyle.paragraph, placeholder='เล่ารายละเอียดเหตุการณ์ที่เกิดขึ้น...')

    async def on_submit(self, interaction: discord.Interaction):
        global ticket_counter
        guild = interaction.guild
        # ดึง Category จากห้องที่กดปุ่ม
        current_category = interaction.channel.category
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel_name = f"การส่งฟ้องห้องที่-{ticket_counter}-รอรับเรื่อง"
        channel = await guild.create_text_channel(name=channel_name, category=current_category, overwrites=overwrites)
        ticket_counter += 1
        
        embed = discord.Embed(title="📄 รายละเอียดการส่งฟ้อง", color=discord.Color.red(), timestamp=datetime.datetime.now())
        embed.add_field(name="⚖️ ข้อมูลผู้ฟ้อง", value=f"**ชื่อ:** {self.u_name}\n**ยศ:** {self.u_rank}\n**สังกัด:** {self.u_branch}\n**ดิสคอร์ด:** {interaction.user.mention}", inline=False)
        embed.add_field(name="👤 ข้อมูลผู้กระทำผิด", value=self.accused_info, inline=False)
        embed.add_field(name="📝 รายละเอียด", value=self.description, inline=False)
        embed.set_footer(text="สำนักพระธรรมนูญ")
        
        await channel.send(embed=embed, view=AdminControlView(ticket_type="filing"))
        await interaction.response.send_message(f"สร้างห้องเรียบร้อยแล้วที่ {channel.mention}", ephemeral=True)

# --- หน้าต่างกรอกข้อมูล (Modal) สำหรับอุทธรณ์ ---
class AppealModal(ui.Modal, title='ศูนย์รับเรื่อง พระธรรมนูญ (ยื่นอุทธรณ์)'):
    u_name = ui.TextInput(label='[ ชื่อบัญชีผู้ยื่น | Username ]')
    u_rank = ui.TextInput(label='[ ยศผู้ยื่น | Rank ]')
    u_branch = ui.TextInput(label='[ สังกัดผู้ยื่น | Branch ]')
    case_num = ui.TextInput(label='[ หมายเลขคดี | Case number ]')
    statement = ui.TextInput(label='[ คำแถลงของฝ่ายจำเลย ]', style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        global ticket_counter
        guild = interaction.guild
        current_category = interaction.channel.category
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel_name = f"การยื่นอุทธรณ์ห้องที่-{ticket_counter}-รอรับเรื่อง"
        channel = await guild.create_text_channel(name=channel_name, category=current_category, overwrites=overwrites)
        ticket_counter += 1

        embed = discord.Embed(title="⚖️ รายละเอียดการยื่นอุทธรณ์", color=discord.Color.blue(), timestamp=datetime.datetime.now())
        embed.add_field(name="👤 ข้อมูลผู้ยื่น", value=f"**ชื่อ:** {self.u_name}\n**ยศ:** {self.u_rank}\n**สังกัด:** {self.u_branch}\n**ดิสคอร์ด:** {interaction.user.mention}", inline=False)
        embed.add_field(name="🔢 หมายเลขคดี", value=self.case_num, inline=True)
        embed.add_field(name="💬 คำแถลง", value=self.statement, inline=False)
        embed.set_footer(text="สำนักพระธรรมนูญ")

        await channel.send(embed=embed, view=AdminControlView(ticket_type="appeal"))
        await interaction.response.send_message(f"สร้างห้องเรียบร้อยแล้วที่ {channel.mention}", ephemeral=True)

# --- ระบบจัดการสำหรับแอดมินในห้อง Ticket ---
class AdminControlView(ui.View):
    def __init__(self, ticket_type):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type

    @ui.button(label="อัปเดตสถานะห้อง", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def update_status(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ เฉพาะผู้ดูแลระบบเท่านั้นที่มีสิทธิ์กดปุ่มนี้!", ephemeral=True)
        
        if self.ticket_type == "filing":
            status_list = ["รอรับเรื่อง", "รอหมายเรียก", "รอรายงานตัว", "รอไต่สวน", "กำลังไต่สวน", "รอพิจารณาคดี", "ปิดคดี", "ยกฟ้อง", "ยกเลิก"]
        else:
            status_list = ["รอรับเรื่อง", "รอพิจารณา", "ปิดคดี", "ยกเลิก"]

        options = [discord.SelectOption(label=s) for s in status_list]
        select = ui.Select(placeholder="เลือกสถานะใหม่เพื่อเปลี่ยนชื่อห้อง...", options=options)

        async def select_callback(inter: discord.Interaction):
            new_status = select.values[0]
            current_name = inter.channel.name
            # แยกชื่อเดิมออกเพื่อเอาเลขห้องไว้ แล้วเปลี่ยนสถานะข้างหลัง
            # ชื่อห้อง format: การส่งฟ้องห้องที่-1-สถานะ
            parts = current_name.split('-')
            if len(parts) >= 3:
                new_name = f"{parts[0]}-{parts[1]}-{new_status}"
                await inter.channel.edit(name=new_name)
                await inter.response.send_message(f"✅ เปลี่ยนสถานะห้องเป็น: **{new_status}**", ephemeral=False)
            else:
                await inter.response.send_message("❌ ไม่สามารถเปลี่ยนชื่อห้องได้เนื่องจากรูปแบบชื่อห้องไม่ถูกต้อง", ephemeral=True)

        select.callback = select_callback
        view = ui.View()
        view.add_item(select)
        await interaction.response.send_message("เลือกสถานะที่ต้องการ:", view=view, ephemeral=True)

    @ui.button(label="ปิดห้อง (ลบ)", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_room(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ เฉพาะผู้ดูแลระบบเท่านั้นที่มีสิทธิ์กดปุ่มนี้!", ephemeral=True)
        
        await interaction.response.send_message("⚠️ กำลังลบห้องนี้ถาวรใน 5 วินาที...")
        import asyncio
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- ปุ่มหน้าแรก ---
class TicketHomeView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="🕵‍♂️ แจ้งความ (ส่งฟ้อง)", style=discord.ButtonStyle.danger, custom_id="btn_filing")
    async def filing_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(FilingModal())

    @ui.button(label="🕵‍♀️ ยื่นอุทธรณ์", style=discord.ButtonStyle.primary, custom_id="btn_appeal")
    async def appeal_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(AppealModal())


@bot.command()
@commands.has_permissions(administrator=True)
async def setup_ticket(ctx):
    embed = discord.Embed(
        title="🏛 ศูนย์รับเรื่อง พระธรรมนูญ",
        description=(
            "โปรดเลือกหมวดหมู่ที่ตรงกับเรื่องของคุณ เพื่อให้เจ้าหน้าที่สามารถช่วยเหลือคุณได้อย่างรวดเร็ว!\n\n"
            "**🕵‍♂️ หมวดหมู่ที่ 1: แจ้งความ (ส่งฟ้อง)**\n"
            "**🕵‍♂️ หมวดหมู่ที่ 2: ยื่นอุทธรณ์ (ยื่นอุทธรณ์เพื่อลดโทษ)**\n\n"
            "**กดปุ่มด้านล่างเพื่อเปิด Ticket | File a complaint**\n"
            "⚠️ **ข้อควรปฏิบัติ:** โปรดเปิด Ticket เฉพาะเมื่อมีเรื่องจริง หากเปิด Ticket มาเล่น หรือไม่แจ้งอะไรเลย อาจถูกลงโทษ "
            "กรุณารอเจ้าหน้าที่ตอบกลับ และให้ข้อมูลอย่างครบถ้วน หากเจ้าหน้าที่ไม่ตอบกลับทันที โปรดรอสักครู่!\n\n"
            "🤝 ขอบคุณที่ให้ความร่วมมือ - สำนักพระธรรมนูญ พร้อมให้บริการ!"
        ),
        color=0xf1c40f # สีทอง
    )
    await ctx.send(embed=embed, view=TicketHomeView())

server_on()

# ใส่ Token บอทของคุณที่นี่
bot.run(os.getenv('TOKEN'))